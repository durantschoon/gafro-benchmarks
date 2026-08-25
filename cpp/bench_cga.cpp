// SPDX-FileCopyrightText: Idiap Research Institute <contact@idiap.ch>
// SPDX-FileContributor: Tobias Loew <tobias.loew@idiap.ch>
// SPDX-FileContributor: Durant Schoon <durant.schoon@gmail.com>
//
// SPDX-License-Identifier: MPL-2.0

#include <chrono>
#include <iostream>
#include <iomanip>
#include <vector>
#include <memory>
#include <string>
#include <gafro/gafro.hpp>

using namespace gafro;
using namespace gafro::cga;
using gafro::math::tau;

struct BenchmarkResult {
    std::string name;
    uint64_t iterations;
    double total_time_ms;
    double ns_per_op;
    double ops_per_sec;
};

template <typename Func>
BenchmarkResult runBenchmark(const std::string &name, uint64_t iterations, Func &&func) {
    // Warmup
    for (uint64_t i = 0; i < iterations / 10 + 1; ++i) {
        func(i);
    }

    auto start = std::chrono::high_resolution_clock::now();
    for (uint64_t i = 0; i < iterations; ++i) {
        func(i);
    }
    auto end = std::chrono::high_resolution_clock::now();

    double total_time_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();
    double total_time_ms = total_time_ns / 1e6;
    double ns_per_op = total_time_ns / static_cast<double>(iterations);
    double ops_per_sec = (static_cast<double>(iterations) / total_time_ns) * 1e9;

    return { name, iterations, total_time_ms, ns_per_op, ops_per_sec };
}

int main(int argc, char **argv) {
    std::vector<BenchmarkResult> results;

    // 1. Geometric Product (Motor composition)
    {
        Translator<double> t1(Translator<double>::Generator({ 1.0, 2.0, 3.0 }));
        Rotor<double> r1(Rotor<double>::Generator({ 0.1, 0.2, 0.3 }), tau / 8.0);
        Motor<double> m1(t1, r1);

        Translator<double> t2(Translator<double>::Generator({ 0.5, -1.0, 1.5 }));
        Rotor<double> r2(Rotor<double>::Generator({ -0.1, 0.4, 0.2 }), tau / 6.0);
        Motor<double> m2(t2, r2);

        volatile double sink = 0.0;

        auto res = runBenchmark("motor_composition_gp", 2'000'000, [&](uint64_t i) {
            Motor<double> prod = m1 * m2;
            sink = prod.get<blades::scalar>();
        });
        results.push_back(res);
    }

    // 2. Sandwich Product on Point
    {
        Translator<double> t(Translator<double>::Generator({ 1.0, 2.0, 3.0 }));
        Rotor<double> r(Rotor<double>::Generator({ 0.1, 0.2, 0.3 }), tau / 8.0);
        Motor<double> m(t, r);
        Point<double> p(Eigen::Vector3d(2.5, -1.5, 4.0));
        volatile double sink = 0.0;

        auto res = runBenchmark("sandwich_point_transform", 2'000'000, [&](uint64_t i) {
            Point<double> p_out = m.apply(p);
            sink = p_out.get<blades::e0>();
        });
        results.push_back(res);
    }

    // 3. Dense Multivector Outer Product
    {
        Point<double> p1(Eigen::Vector3d(1.0, 0.0, 0.0));
        Point<double> p2(Eigen::Vector3d(0.0, 1.0, 0.0));
        volatile double sink = 0.0;

        auto res = runBenchmark("point_pair_outer_product", 2'000'000, [&](uint64_t i) {
            auto pp = p1 ^ p2;
            sink = pp.template get<blades::e01>();
        });
        results.push_back(res);
    }

    // 4. Forward Kinematics 6-DOF
    {
        std::vector<std::unique_ptr<RevoluteJoint<double>>> joints;
        KinematicChain<double> chain;
        for (int i = 0; i < 6; ++i) {
            auto joint = std::make_unique<RevoluteJoint<double>>();
            joint->setFrame(Motor<double>(Translator<double>::Generator({ 0.0, 0.2, 0.0 })));
            joint->setAxis(RevoluteJoint<double>::Axis({ (i % 2 == 0) ? 1.0 : 0.0, 0.0, (i % 2 == 0) ? 0.0 : 1.0 }));
            chain.addActuatedJoint(joint.get());
            joints.push_back(std::move(joint));
        }

        Eigen::Matrix<double, 6, 1> q;
        q << tau / 8.0, tau / 4.0, -tau / 8.0, tau / 6.0, 0.0, tau / 4.0;
        volatile double sink = 0.0;

        auto res = runBenchmark("kinematics_fk_6dof", 500'000, [&](uint64_t i) {
            Motor<double> fk = chain.computeMotor(q);
            sink = fk.get<blades::scalar>();
        });
        results.push_back(res);
    }

    // 5. Geometric Jacobian 6-DOF
    {
        std::vector<std::unique_ptr<RevoluteJoint<double>>> joints;
        KinematicChain<double> chain;
        for (int i = 0; i < 6; ++i) {
            auto joint = std::make_unique<RevoluteJoint<double>>();
            joint->setFrame(Motor<double>(Translator<double>::Generator({ 0.0, 0.2, 0.0 })));
            joint->setAxis(RevoluteJoint<double>::Axis({ (i % 2 == 0) ? 1.0 : 0.0, 0.0, (i % 2 == 0) ? 0.0 : 1.0 }));
            chain.addActuatedJoint(joint.get());
            joints.push_back(std::move(joint));
        }

        Eigen::Matrix<double, 6, 1> q;
        q << tau / 8.0, tau / 4.0, -tau / 8.0, tau / 6.0, 0.0, tau / 4.0;
        volatile double sink = 0.0;

        auto res = runBenchmark("kinematics_geometric_jacobian_6dof", 500'000, [&](uint64_t i) {
            auto jac = chain.computeGeometricJacobian(q);
            sink = jac.getCoefficient(0, 0).template get<blades::e12>();
        });
        results.push_back(res);
    }

    // Output JSON
    bool json_output = (argc > 1 && std::string(argv[1]) == "--json");

    if (json_output) {
        std::cout << "{\n";
        std::cout << "  \"language\": \"cpp\",\n";
        std::cout << "  \"implementation\": \"gafro-cpp (C++26)\",\n";
        std::cout << "  \"results\": [\n";
        for (size_t i = 0; i < results.size(); ++i) {
            const auto &r = results[i];
            std::cout << "    {\n";
            std::cout << "      \"benchmark\": \"" << r.name << "\",\n";
            std::cout << "      \"iterations\": " << r.iterations << ",\n";
            std::cout << "      \"total_time_ms\": " << std::fixed << std::setprecision(4) << r.total_time_ms << ",\n";
            std::cout << "      \"time_per_op_ns\": " << std::fixed << std::setprecision(2) << r.ns_per_op << ",\n";
            std::cout << "      \"ops_per_sec\": " << std::fixed << std::setprecision(0) << r.ops_per_sec << "\n";
            std::cout << "    }" << (i + 1 < results.size() ? "," : "") << "\n";
        }
        std::cout << "  ]\n";
        std::cout << "}\n";
    } else {
        std::cout << "\n================ Gafro C++26 Performance Benchmarks ================\n";
        std::cout << std::left << std::setw(35) << "Benchmark" 
                  << std::right << std::setw(12) << "Iterations" 
                  << std::setw(15) << "Time (ms)" 
                  << std::setw(15) << "ns / op" 
                  << std::setw(18) << "ops / sec" << "\n";
        std::cout << std::string(95, '-') << "\n";
        for (const auto &r : results) {
            std::cout << std::left << std::setw(35) << r.name 
                      << std::right << std::setw(12) << r.iterations 
                      << std::setw(15) << std::fixed << std::setprecision(2) << r.total_time_ms 
                      << std::setw(15) << std::fixed << std::setprecision(2) << r.ns_per_op 
                      << std::setw(18) << std::fixed << std::setprecision(0) << r.ops_per_sec << "\n";
        }
        std::cout << std::string(95, '=') << "\n\n";
    }

    return 0;
}
