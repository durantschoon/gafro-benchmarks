// SPDX-FileCopyrightText: Idiap Research Institute <contact@idiap.ch>
// SPDX-FileContributor: Tobias Loew <tobias.loew@idiap.ch>
// SPDX-FileContributor: Durant Schoon <durant.schoon@gmail.com>
//
// SPDX-License-Identifier: MPL-2.0

use std::hint::black_box;
use std::time::Instant;
use std::env;

use gafro::algebra::blades::*;
use gafro::algebra::cga::point::Point;
use gafro::algebra::cga::rotor::Rotor;
use gafro::algebra::cga::translator::Translator;
use gafro::algebra::cga::motor::Motor;
use gafro::robots::joint::Joint;
use gafro::robots::kinematic_chain::KinematicChain;
use gafro::constants::TAU;

struct BenchmarkResult {
    name: &'static str,
    iterations: u64,
    total_time_ms: f64,
    ns_per_op: f64,
    ops_per_sec: f64,
}

fn run_benchmark<F>(name: &'static str, iterations: u64, mut func: F) -> BenchmarkResult
where
    F: FnMut(u64),
{
    // Warmup
    for i in 0..(iterations / 10 + 1) {
        func(i);
    }

    let start = Instant::now();
    for i in 0..iterations {
        func(i);
    }
    let elapsed = start.elapsed();

    let total_time_ns = elapsed.as_nanos() as f64;
    let total_time_ms = total_time_ns / 1e6;
    let ns_per_op = total_time_ns / iterations as f64;
    let ops_per_sec = (iterations as f64 / total_time_ns) * 1e9;

    BenchmarkResult {
        name,
        iterations,
        total_time_ms,
        ns_per_op,
        ops_per_sec,
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let json_output = args.len() > 1 && args[1] == "--json";

    let mut results = Vec::new();

    // 1. Geometric Product (Motor composition)
    {
        let t1 = Translator::from_displacement(1.0, 2.0, 3.0);
        let r1 = Rotor::from_axis_angle(0.1, 0.2, 0.3, TAU / 8.0);
        let m1 = Motor::from_translator_rotor(&t1, &r1);

        let t2 = Translator::from_displacement(0.5, -1.0, 1.5);
        let r2 = Rotor::from_axis_angle(-0.1, 0.4, 0.2, TAU / 6.0);
        let m2 = Motor::from_translator_rotor(&t2, &r2);

        let res = run_benchmark("motor_composition_gp", 2_000_000, |_| {
            let prod = black_box(m1) * black_box(m2);
            black_box(prod.scalar());
        });
        results.push(res);
    }

    // 2. Sandwich Product on Point
    {
        let t = Translator::from_displacement(1.0, 2.0, 3.0);
        let r = Rotor::from_axis_angle(0.1, 0.2, 0.3, TAU / 8.0);
        let m = Motor::from_translator_rotor(&t, &r);
        let p = Point::new(2.5, -1.5, 4.0);

        let res = run_benchmark("sandwich_point_transform", 2_000_000, |_| {
            let p_out = black_box(&m).apply(black_box(&p));
            black_box(p_out.mv.get(E0));
        });
        results.push(res);
    }

    // 3. Dense Multivector Outer Product
    {
        let p1 = Point::new(1.0, 0.0, 0.0);
        let p2 = Point::new(0.0, 1.0, 0.0);

        let res = run_benchmark("point_pair_outer_product", 2_000_000, |_| {
            let pp = black_box(p1.mv) ^ black_box(p2.mv);
            black_box(pp.get(E01));
        });
        results.push(res);
    }

    // 4. Forward Kinematics 6-DOF
    {
        let mut chain = KinematicChain::new();
        for i in 0..6 {
            let trans = Translator::from_displacement(0.0, 0.2, 0.0);
            let axis = if i % 2 == 0 { [0.0, 0.0, 1.0] } else { [1.0, 0.0, 0.0] };
            chain.add_joint(Joint::revolute(axis, Motor::from(trans)));
        }

        let q = [TAU / 8.0, TAU / 4.0, -TAU / 8.0, TAU / 6.0, 0.0, TAU / 4.0];

        let res = run_benchmark("kinematics_fk_6dof", 500_000, |_| {
            let fk = black_box(&chain).forward_kinematics(black_box(&q));
            black_box(fk.scalar());
        });
        results.push(res);
    }

    // 5. Geometric Jacobian 6-DOF
    {
        let mut chain = KinematicChain::new();
        for i in 0..6 {
            let trans = Translator::from_displacement(0.0, 0.2, 0.0);
            let axis = if i % 2 == 0 { [0.0, 0.0, 1.0] } else { [1.0, 0.0, 0.0] };
            chain.add_joint(Joint::revolute(axis, Motor::from(trans)));
        }

        let q = [TAU / 8.0, TAU / 4.0, -TAU / 8.0, TAU / 6.0, 0.0, TAU / 4.0];

        let res = run_benchmark("kinematics_geometric_jacobian_6dof", 500_000, |_| {
            let jac = black_box(&chain).geometric_jacobian(black_box(&q));
            black_box(jac[0].e12());
        });
        results.push(res);
    }

    if json_output {
        println!("{{");
        println!("  \"language\": \"rust\",");
        println!("  \"implementation\": \"gafro-rust\",");
        println!("  \"results\": [");
        for (i, r) in results.iter().enumerate() {
            println!("    {{");
            println!("      \"benchmark\": \"{}\",", r.name);
            println!("      \"iterations\": {},", r.iterations);
            println!("      \"total_time_ms\": {:.4},", r.total_time_ms);
            println!("      \"time_per_op_ns\": {:.2},", r.ns_per_op);
            println!("      \"ops_per_sec\": {:.0}", r.ops_per_sec);
            print!("    }}");
            if i + 1 < results.len() {
                println!(",");
            } else {
                println!();
            }
        }
        println!("  ]");
        println!("}}");
    } else {
        println!("\n================ Gafro Rust Performance Benchmarks ================");
        println!(
            "{:<35} {:>12} {:>15} {:>15} {:>18}",
            "Benchmark", "Iterations", "Time (ms)", "ns / op", "ops / sec"
        );
        println!("{}", "-".repeat(95));
        for r in &results {
            println!(
                "{:<35} {:>12} {:>15.2} {:>15.2} {:>18.0}",
                r.name, r.iterations, r.total_time_ms, r.ns_per_op, r.ops_per_sec
            );
        }
        println!("{}\n", "=".repeat(95));
    }
}
