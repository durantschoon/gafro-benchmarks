#include <algorithm>
#include <array>
#include <cassert>  // gafro-cpp's MultivectorMatrix.hxx uses assert without including it
#include <chrono>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <memory>
#include <numbers>
#include <stdexcept>
#include <string>
#include <vector>
// Only the layers these workloads use. The gafro/gafro.hpp umbrella also pulls
// in gafro/modern/, which clang rejects at the current gafro-cpp revision
// (ambiguous ModernMotor between gafro::modern and gafro::cuda::modern).
#include <gafro/gafro_package_config.hpp>
#include <gafro/algebra.hpp>
#include <gafro/physics.hpp>
#include <gafro/robot.hpp>
#include <gafro/simd/BatchMotorSoA.hpp>
#include <gafro/simd/BatchPointSoA.hpp>

#ifndef GAFRO_BENCH_COMPILER
#define GAFRO_BENCH_COMPILER "unknown"
#endif
#ifndef GAFRO_BENCH_FLAGS
#define GAFRO_BENCH_FLAGS "unknown"
#endif
// The adapter process's own kernel and architecture, spelled like Python's
// platform.system()/platform.machine(), so the report compares like with like.
#if defined(__APPLE__)
#define GAFRO_BENCH_SYSTEM "Darwin"
#elif defined(__linux__)
#define GAFRO_BENCH_SYSTEM "Linux"
#else
#define GAFRO_BENCH_SYSTEM "unknown"
#endif
#if defined(__aarch64__) || defined(__arm64__)
#define GAFRO_BENCH_MACHINE "arm64"
#elif defined(__x86_64__)
#define GAFRO_BENCH_MACHINE "x86_64"
#else
#define GAFRO_BENCH_MACHINE "unknown"
#endif
using namespace gafro;
using namespace gafro::cga;
namespace {
struct Result {
    std::string id;
    std::vector<double> durations;
    double oracle{0.0};
    std::uint64_t warmup_operations{0};
    std::uint64_t operations_per_sample{0};
    std::size_t batch_size{0};  // 0 for scalar workloads
};
template <class T> inline void do_not_optimize(T const &value) {
#if defined(__GNUC__) || defined(__clang__)
    asm volatile("" : : "g"(&value) : "memory");
#else
    (void)value;
#endif
}
void require_close(const char *id, double actual, double expected) {
    if (!std::isfinite(actual) || std::abs(actual - expected) > 1e-10)
        throw std::runtime_error(std::string(id) + " oracle mismatch: expected " + std::to_string(expected) + ", got " + std::to_string(actual));
}
// Times `invocations` calls of `operation` per sample. Each call processes
// `batch_size` items (one for scalar workloads), so the reported operation
// counts are invocations times items.
template <class Operation>
Result measure(std::string id, std::uint64_t warmup, std::uint64_t invocations, int samples, double expected,
               Operation operation, std::size_t batch_size = 0) {
    require_close(id.c_str(), operation(0), expected);
    double warmup_accumulator = 0.0;
    for (std::uint64_t i = 0; i < warmup; ++i) warmup_accumulator += operation(i);
    do_not_optimize(warmup_accumulator);
    const std::uint64_t items = batch_size == 0 ? 1 : batch_size;
    Result result{std::move(id), {}, expected, warmup * items, invocations * items, batch_size};
    for (int sample = 0; sample < samples; ++sample) {
        const auto start = std::chrono::high_resolution_clock::now();
        double accumulator = 0.0;
        for (std::uint64_t i = 0; i < invocations; ++i) accumulator += operation(i);
        const auto stop = std::chrono::high_resolution_clock::now();
        do_not_optimize(accumulator);
        const double raw_ns = std::chrono::duration<double, std::nano>(stop - start).count();
        // A smoke sample of one small batch can finish inside one clock tick;
        // like the Rust adapter, floor batch samples at 1 ns. Scalar samples
        // always span many ticks, so a zero there still means a broken loop.
        const double ns = batch_size == 0 ? raw_ns : std::max(1.0, raw_ns);
        if (!std::isfinite(ns) || ns <= 0.0) throw std::runtime_error(result.id + ": non-positive timing");
        result.durations.push_back(ns);
    }
    return result;
}

// Batch workloads: the smoke profile times one invocation (batch_size items);
// the full profile times 16384 items and warms up 4096, as the manifest says.
struct BatchPlan { std::uint64_t warmup_invocations; std::uint64_t sample_invocations; int samples; };
template <std::size_t N> constexpr BatchPlan batch_plan(bool smoke) {
    return smoke ? BatchPlan{1, 1, 3}
                 : BatchPlan{std::max<std::uint64_t>(1, 4096 / N), std::max<std::uint64_t>(1, 16384 / N), 15};
}

// Composes N translation motors element-wise in gafro-cpp's BatchMotorSoA.
// Packing happens once before timing; every lane of both composition orders
// is checked against the scalar Motor product before any timed work.
template <std::size_t N>
Result batch_motor(bool smoke, const std::string &id) {
    using Batch = simd::BatchMotorSoA<double, N>;
    const Motor<double> first{Translator<double>{Translator<double>::Generator({1.0, 2.0, 3.0})}};
    const Motor<double> second{Translator<double>{Translator<double>::Generator({-0.5, 0.25, 1.5})}};
    const std::vector<Motor<double>> firsts(N, first);
    const std::vector<Motor<double>> seconds(N, second);
    const auto left = std::make_unique<Batch>(Batch::from_motors(firsts));
    const auto right = std::make_unique<Batch>(Batch::from_motors(seconds));
    const auto out = std::make_unique<Batch>();
    const auto operation = [&](std::uint64_t i) -> double {
        if (i % 2 == 0) left->compose(*right, *out);
        else right->compose(*left, *out);
        do_not_optimize(*out);
        return out->blades[0][0];
    };
    // BatchMotorSoA blade order: scalar, e12, e13, e23, e1i, e2i, e3i, e123i.
    const auto coefficients = [](const Motor<double> &motor) {
        return std::array<double, simd::MOTOR_BLADE_COUNT>{
            motor.template get<blades::scalar>(), motor.template get<blades::e12>(),
            motor.template get<blades::e13>(), motor.template get<blades::e23>(),
            motor.template get<blades::e1i>(), motor.template get<blades::e2i>(),
            motor.template get<blades::e3i>(), motor.template get<blades::e123i>()};
    };
    const std::array<std::array<double, simd::MOTOR_BLADE_COUNT>, 2> references{
        coefficients(Motor<double>(first * second)), coefficients(Motor<double>(second * first))};
    for (std::uint64_t order = 0; order < 2; ++order) {
        operation(order);
        for (std::size_t lane = 0; lane < N; ++lane)
            for (std::size_t blade = 0; blade < simd::MOTOR_BLADE_COUNT; ++blade)
                require_close(id.c_str(), out->blades[blade][lane], references[order][blade]);
    }
    const BatchPlan plan = batch_plan<N>(smoke);
    return measure(id, plan.warmup_invocations, plan.sample_invocations, plan.samples, 1.0, operation, N);
}

// Transforms N points by one translation motor in gafro-cpp's BatchPointSoA.
// Every output lane is checked against the scalar Motor::apply result and the
// analytic translation (3.5, 0.5, 7.0) before any timed work.
template <std::size_t N>
Result batch_point(bool smoke, const std::string &id) {
    using Batch = simd::BatchPointSoA<double, N>;
    const Motor<double> motor{Translator<double>{Translator<double>::Generator({1.0, 2.0, 3.0})}};
    const Point<double> point(2.5, -1.5, 4.0);
    const std::vector<Point<double>> points(N, point);
    const auto input = std::make_unique<Batch>(Batch::from_points(points));
    const auto out = std::make_unique<Batch>();
    const auto operation = [&](std::uint64_t) -> double {
        input->transform(motor, *out);
        do_not_optimize(*out);
        return out->x[0];
    };
    const auto moved = motor.apply(point);
    const std::array<double, 3> scalar{moved.template get<blades::e1>(), moved.template get<blades::e2>(),
                                       moved.template get<blades::e3>()};
    const std::array<double, 3> analytic{3.5, 0.5, 7.0};
    for (std::size_t axis = 0; axis < 3; ++axis) require_close(id.c_str(), scalar[axis], analytic[axis]);
    operation(0);
    for (std::size_t lane = 0; lane < N; ++lane) {
        require_close(id.c_str(), out->x[lane], analytic[0]);
        require_close(id.c_str(), out->y[lane], analytic[1]);
        require_close(id.c_str(), out->z[lane], analytic[2]);
    }
    const BatchPlan plan = batch_plan<N>(smoke);
    return measure(id, plan.warmup_invocations, plan.sample_invocations, plan.samples, 3.5, operation, N);
}

std::string argument(int argc, char **argv, const std::string &key, const std::string &fallback) {
    for (int i = 1; i + 1 < argc; ++i) if (argv[i] == key) return argv[i + 1];
    return fallback;
}
}
int main(int argc, char **argv) try {
    const bool smoke = argument(argc, argv, "--profile", "full") == "smoke";
    const std::uint64_t warmup = smoke ? 8 : 1000;
    const std::uint64_t operations = smoke ? 1000 : 10000;
    const int samples = smoke ? 3 : 15;
    const std::string revision = argument(argc, argv, "--revision", "unknown");
    const std::string dirty = argument(argc, argv, "--dirty", "false");
    const std::vector<Eigen::Vector3d> translations{{1.0, 2.0, 3.0}, {-0.5, 0.25, 1.5}};
    const std::vector<Eigen::Vector3d> points{{2.5, -1.5, 4.0}, {3.0, 2.0, -1.0}};
    const std::vector<Motor<double>> motors{
        Motor<double>{Translator<double>{Translator<double>::Generator(translations[0])}},
        Motor<double>{Translator<double>{Translator<double>::Generator(translations[1])}}};
    const Rotor<double>::Generator rotor_axis({0.0, 0.0, 1.0});
    const std::vector<Point<double>> conformal_points{Point<double>(points[0]), Point<double>(points[1])};
    const std::vector<Point<double>> outer_left{
        Point<double>(Eigen::Vector3d(1.0, 0.0, 0.0)), Point<double>(Eigen::Vector3d(1.125, 0.0, 0.0))};
    const std::vector<Point<double>> outer_right{
        Point<double>(Eigen::Vector3d(0.0, 1.0, 0.0)), Point<double>(Eigen::Vector3d(0.0, 1.0 / 1.125, 0.0))};
    RevoluteJoint<double> robotics_joint_0;
    RevoluteJoint<double> robotics_joint_1;
    const Motor<double> robotics_frame(Translator<double>(Translator<double>::Generator({0.0, 1.0, 0.0})));
    robotics_joint_0.setAxis(RevoluteJoint<double>::Axis({1.0, 0.0, 0.0}));
    robotics_joint_1.setAxis(RevoluteJoint<double>::Axis({1.0, 0.0, 0.0}));
    robotics_joint_0.setFrame(robotics_frame);
    robotics_joint_1.setFrame(robotics_frame);
    KinematicChain<double> robotics_chain("canonical-2r");
    robotics_chain.addActuatedJoint(&robotics_joint_0);
    robotics_chain.addActuatedJoint(&robotics_joint_1);
    const std::vector<Eigen::Vector2d> robotics_positions{
        Eigen::Vector2d(0.0, std::numbers::pi / 2.0),
        Eigen::Vector2d(1.0 / 1024.0, std::numbers::pi / 2.0 - 1.0 / 1024.0)};
    const Motor<double> robotics_oracle_motor = robotics_chain.computeMotor<2>(robotics_positions[0]);
    require_close("robotics FK scalar", robotics_oracle_motor.template get<blades::scalar>(), std::sqrt(0.5));
    require_close("robotics FK e12", robotics_oracle_motor.template get<blades::e12>(), -std::sqrt(0.5));
    require_close("robotics FK e13", robotics_oracle_motor.template get<blades::e13>(), 0.0);
    require_close("robotics FK e23", robotics_oracle_motor.template get<blades::e23>(), 0.0);
    require_close("robotics FK e1i", robotics_oracle_motor.template get<blades::e1i>(), -std::sqrt(0.5));
    require_close("robotics FK e2i", robotics_oracle_motor.template get<blades::e2i>(), -std::sqrt(0.5));
    require_close("robotics FK e3i", robotics_oracle_motor.template get<blades::e3i>(), 0.0);
    require_close("robotics FK e123i", robotics_oracle_motor.template get<blades::e123i>(), 0.0);
    const auto robotics_oracle_jacobian = robotics_chain.computeGeometricJacobian<2>(robotics_positions[0]);
    const double robotics_expected_jacobian[2][6]{{1.0, 0.0, 0.0, 1.0, 0.0, 0.0}, {1.0, 0.0, 0.0, 2.0, 0.0, 0.0}};
    for (int column = 0; column < 2; ++column) {
        const auto &twist = robotics_oracle_jacobian.getCoefficient(0, column);
        const double actual[6]{twist.template get<blades::e12>(), twist.template get<blades::e13>(),
            twist.template get<blades::e23>(), twist.template get<blades::e1i>(),
            twist.template get<blades::e2i>(), twist.template get<blades::e3i>()};
        for (int coefficient = 0; coefficient < 6; ++coefficient)
            require_close("robotics Jacobian coefficient", actual[coefficient], robotics_expected_jacobian[column][coefficient]);
    }
    std::vector<Result> results;
    using Dense = Multivector<double,
        0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
        16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31>;
    const Dense dense_left(Eigen::Matrix<double, 32, 1>::Ones());
    Eigen::Matrix<double, 32, 1> dense_right_values = Eigen::Matrix<double, 32, 1>::Ones();
    dense_right_values[0] = 2.0;
    const Dense dense_right(dense_right_values);
    results.push_back(measure("dense_geometric_product/f64/scalar", warmup, operations, samples, 1.0, [&](std::uint64_t i) {
        return i % 2 == 0 ? Dense(dense_left * dense_right).template get<blades::scalar>()
                          : Dense(dense_right * dense_left).template get<blades::scalar>();
    }));
    results.push_back(measure("motor_composition_gp/f64/scalar", warmup, operations, samples, 1.0, [&](std::uint64_t i) {
        return Motor<double>(motors[i % 2] * motors[(i + 1) % 2]).template get<blades::scalar>();
    }));
    results.push_back(measure("sandwich_point_transform/f64/e1", warmup, operations, samples, 3.5, [&](std::uint64_t i) {
        return motors[i % 2].apply(conformal_points[i % 2]).template get<blades::e1>();
    }));
    results.push_back(measure("point_pair_outer_product/f64/e12", warmup, operations, samples, 1.0, [&](std::uint64_t i) {
        return (outer_left[i % 2] ^ outer_right[i % 2]).template get<blades::e12>();
    }));
    results.push_back(measure("rotor_construction/f64/scalar", warmup, operations, samples, std::sqrt(0.5), [&](std::uint64_t i) {
        const Rotor<double> rotor(rotor_axis, (i % 2 == 0) ? std::numbers::pi / 2.0 : std::numbers::pi / 2.0);
        return rotor.template get<blades::scalar>();
    }));
    results.push_back(measure("translator_construction/f64/e1i", warmup, operations, samples, -0.5, [&](std::uint64_t) {
        const Translator<double> translator{Translator<double>::Generator(translations[0])};
        require_close("translator construction e2i", translator.template get<blades::e2i>(), -1.0);
        require_close("translator construction e3i", translator.template get<blades::e3i>(), -1.5);
        return translator.template get<blades::e1i>();
    }));
    results.push_back(measure("robotics_forward_kinematics_2r/f64/motor_checksum", warmup, operations, samples, -std::sqrt(2.0), [&](std::uint64_t i) {
        const Motor<double> motor = robotics_chain.computeMotor<2>(robotics_positions[i % 2]);
        return motor.template get<blades::scalar>() + motor.template get<blades::e12>() +
               motor.template get<blades::e13>() + motor.template get<blades::e23>() +
               motor.template get<blades::e1i>() + motor.template get<blades::e2i>() +
               motor.template get<blades::e3i>() + motor.template get<blades::e123i>();
    }));
    results.push_back(measure("robotics_geometric_jacobian_2r/f64/base_checksum", warmup, operations, samples, 5.0, [&](std::uint64_t i) {
        const auto jacobian = robotics_chain.computeGeometricJacobian<2>(robotics_positions[i % 2]);
        double checksum = 0.0;
        for (int column = 0; column < 2; ++column) {
            const auto &twist = jacobian.getCoefficient(0, column);
            checksum += twist.template get<blades::e12>() + twist.template get<blades::e13>() +
                        twist.template get<blades::e23>() + twist.template get<blades::e1i>() +
                        twist.template get<blades::e2i>() + twist.template get<blades::e3i>();
        }
        return checksum;
    }));
    const Inertia<double> physics_inertia(2.0, 0.5, 0.0, 0.0, 0.5, 0.0, 0.8);
    Twist<double> physics_twist;
    physics_twist.template set<blades::e1i>(1.0);
    physics_twist.template set<blades::e2i>(2.0);
    physics_twist.template set<blades::e3i>(3.0);
    physics_twist.template set<blades::e12>(0.1);
    physics_twist.template set<blades::e13>(0.2);
    physics_twist.template set<blades::e23>(0.3);
    const Wrench<double> oracle_wrench = physics_inertia(physics_twist);
    require_close("physics wrench f1", oracle_wrench.template get<blades::e01>(), 2.0);
    require_close("physics wrench f2", oracle_wrench.template get<blades::e02>(), 4.0);
    require_close("physics wrench tau12", oracle_wrench.template get<blades::e12>(), 0.08);
    require_close("physics wrench f3", oracle_wrench.template get<blades::e03>(), 6.0);
    require_close("physics wrench tau13", oracle_wrench.template get<blades::e13>(), 0.10);
    require_close("physics wrench tau23", oracle_wrench.template get<blades::e23>(), 0.15);
    results.push_back(measure("spatial_inertia_action/f64/wrench_checksum", warmup, operations, samples, 12.33, [&](std::uint64_t) {
        const Wrench<double> wrench = physics_inertia(physics_twist);
        return wrench.template get<blades::e01>() + wrench.template get<blades::e02>() +
               wrench.template get<blades::e12>() + wrench.template get<blades::e03>() +
               wrench.template get<blades::e13>() + wrench.template get<blades::e23>();
    }));
    results.push_back(measure("spatial_inertia_transform/f64/e01_mass", warmup, operations, samples, 2.0, [&](std::uint64_t) {
        const Inertia<double> transformed = physics_inertia.transform(motors[0]);
        return transformed.getElement01().template get<blades::e01>();
    }));

    results.push_back(batch_motor<16>(smoke, "batch_motor_composition/f64/n16/scalar_lane0"));
    results.push_back(batch_motor<256>(smoke, "batch_motor_composition/f64/n256/scalar_lane0"));
    results.push_back(batch_motor<4096>(smoke, "batch_motor_composition/f64/n4096/scalar_lane0"));
    results.push_back(batch_point<16>(smoke, "batch_point_transform/f64/n16/e1_lane0"));
    results.push_back(batch_point<256>(smoke, "batch_point_transform/f64/n256/e1_lane0"));
    results.push_back(batch_point<4096>(smoke, "batch_point_transform/f64/n4096/e1_lane0"));
    const std::string host_base = std::string("\"clock\":\"high_resolution_clock\",\"system\":\"") +
                                  GAFRO_BENCH_SYSTEM + "\",\"machine\":\"" + GAFRO_BENCH_MACHINE + "\"";
    std::cout << std::setprecision(17) << "{\"results\":[";
    for (std::size_t index = 0; index < results.size(); ++index) {
        const auto &result = results[index];
        if (index) std::cout << ',';
        // Batch rows describe the SoA measurement boundary, as the Rust adapter does.
        const std::string host = result.batch_size == 0 ? "{" + host_base + "}" :
            "{" + host_base + ",\"threads\":1,\"simd\":\"compiler-target\",\"alignment\":\"native\",\"batch_size\":" +
            std::to_string(result.batch_size) + ",\"layout\":\"structure-of-arrays\",\"packing\":\"excluded\","
            "\"allocation\":\"excluded\",\"output_validation\":\"all_lanes\"}";
        std::cout << "{\"schema_version\":\"gafro-benchmark-result/v1\",\"implementation\":{\"family\":\"cpp\",\"name\":\"gafro-cpp\","
                  << "\"repository_revision\":\"" << revision << "\",\"dirty\":" << dirty << ','
                  << "\"compiler\":\"" << GAFRO_BENCH_COMPILER << "\",\"backend\":\"cpu-scalar\",\"flags\":[\"" << GAFRO_BENCH_FLAGS << "\"]},"
                  << "\"host\":" << host << ",\"workload_id\":\"" << result.id << "\",\"status\":\"supported\",\"reason\":\"\","
                  << "\"warmup_operations\":" << result.warmup_operations << ",\"operations_per_sample\":" << result.operations_per_sample << ",\"sample_durations_ns\":[";
        for (std::size_t sample = 0; sample < result.durations.size(); ++sample) { if (sample) std::cout << ','; std::cout << result.durations[sample]; }
        std::cout << "],\"oracle\":{\"value\":" << result.oracle << "}}";
    }
    std::cout << "]}\n"; return 0;
} catch (const std::exception &error) { std::cerr << "benchmark failed: " << error.what() << '\n'; return 2; }
