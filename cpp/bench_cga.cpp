#include <chrono>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <numbers>
#include <stdexcept>
#include <string>
#include <vector>
#include <gafro/gafro.hpp>
#ifndef GAFRO_BENCH_COMPILER
#define GAFRO_BENCH_COMPILER "unknown"
#endif
#ifndef GAFRO_BENCH_FLAGS
#define GAFRO_BENCH_FLAGS "unknown"
#endif
using namespace gafro;
using namespace gafro::cga;
namespace {
struct Result { std::string id; std::vector<double> durations; double oracle; };
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
template <class Operation>
Result measure(std::string id, std::uint64_t warmup, std::uint64_t operations, int samples, double expected, Operation operation) {
    require_close(id.c_str(), operation(0), expected);
    double warmup_accumulator = 0.0;
    for (std::uint64_t i = 0; i < warmup; ++i) warmup_accumulator += operation(i);
    do_not_optimize(warmup_accumulator);
    Result result{std::move(id), {}, expected};
    for (int sample = 0; sample < samples; ++sample) {
        const auto start = std::chrono::high_resolution_clock::now();
        double accumulator = 0.0;
        for (std::uint64_t i = 0; i < operations; ++i) accumulator += operation(i);
        const auto stop = std::chrono::high_resolution_clock::now();
        do_not_optimize(accumulator);
        const double ns = std::chrono::duration<double, std::nano>(stop - start).count();
        if (!std::isfinite(ns) || ns <= 0.0) throw std::runtime_error("non-finite timing");
        result.durations.push_back(ns);
    }
    return result;
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
    const std::vector<std::string> unsupported{
        "batch_motor_composition/f64/n16/scalar_lane0",
        "batch_motor_composition/f64/n256/scalar_lane0",
        "batch_motor_composition/f64/n4096/scalar_lane0",
        "batch_point_transform/f64/n16/e1_lane0",
        "batch_point_transform/f64/n256/e1_lane0",
        "batch_point_transform/f64/n4096/e1_lane0"};
    std::cout << std::setprecision(17) << "{\"results\":[";
    for (std::size_t index = 0; index < results.size(); ++index) {
        const auto &result = results[index]; if (index) std::cout << ',';
        std::cout << "{\"schema_version\":\"gafro-benchmark-result/v1\",\"implementation\":{\"family\":\"cpp\",\"name\":\"gafro-cpp\","
                  << "\"repository_revision\":\"" << revision << "\",\"dirty\":" << dirty << ','
                  << "\"compiler\":\"" << GAFRO_BENCH_COMPILER << "\",\"backend\":\"cpu-scalar\",\"flags\":[\"" << GAFRO_BENCH_FLAGS << "\"]},"
                  << "\"host\":{\"clock\":\"high_resolution_clock\"},\"workload_id\":\"" << result.id << "\",\"status\":\"supported\",\"reason\":\"\","
                  << "\"warmup_operations\":" << warmup << ",\"operations_per_sample\":" << operations << ",\"sample_durations_ns\":[";
        for (std::size_t sample = 0; sample < result.durations.size(); ++sample) { if (sample) std::cout << ','; std::cout << result.durations[sample]; }
        std::cout << "],\"oracle\":{\"value\":" << result.oracle << "}}";
    }
    for (const auto &id : unsupported) {
        std::cout << ",{\"schema_version\":\"gafro-benchmark-result/v1\",\"implementation\":{\"family\":\"cpp\",\"name\":\"gafro-cpp\","
                  << "\"repository_revision\":\"" << revision << "\",\"dirty\":" << dirty << ','
                  << "\"compiler\":\"" << GAFRO_BENCH_COMPILER << "\",\"backend\":\"cpu-scalar\",\"flags\":[\"" << GAFRO_BENCH_FLAGS << "\"]},"
                  << "\"host\":{},\"workload_id\":\"" << id << "\",\"status\":\"unsupported\","
                  << "\"reason\":\"gafro-cpp CPU adapter has no contract SoA batch API\"}";
    }
    std::cout << "]}\n"; return 0;
} catch (const std::exception &error) { std::cerr << "benchmark failed: " << error.what() << '\n'; return 2; }
