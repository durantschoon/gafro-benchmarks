use std::env;
use std::hint::black_box;
use std::time::Instant;

use gafro::algebra::blades::E12;
use gafro::algebra::OrthogonalMultivector32;
use gafro::algebra::cga::batch_motor::BatchMotorSoA;
use gafro::algebra::cga::batch_point::BatchPointSoA;
use gafro::algebra::cga::motor::Motor;
use gafro::algebra::cga::rotor::Rotor;
use gafro::algebra::cga::point::Point;
use gafro::algebra::cga::translator::Translator;
use gafro::robots::{Joint, KinematicChain};

struct Provenance { revision: String, dirty: bool, compiler: String, target: String, flags: String }

struct ResultRow {
    id: &'static str, status: &'static str, reason: &'static str,
    warmup_operations: u64, operations_per_sample: u64,
    durations_ns: Vec<u128>, oracle: Option<f64>,
}

fn argument(args: &[String], key: &str, fallback: &str) -> String {
    args.windows(2).find(|p| p[0] == key).map(|p| p[1].clone()).unwrap_or_else(|| fallback.to_owned())
}

fn require_close(id: &str, actual: f64, expected: f64) {
    if !actual.is_finite() || (actual - expected).abs() > 1.0e-10 {
        panic!("{id} oracle mismatch: expected {expected}, got {actual}");
    }
}

fn measure<F>(id: &'static str, expected: f64, warmup_invocations: u64,
    sample_invocations: u64, operations_per_invocation: u64, sample_count: usize,
    mut operation: F) -> ResultRow
where F: FnMut(u64) -> f64 {
    require_close(id, operation(0), expected);
    let mut warmup_accumulator = 0.0;
    for index in 0..warmup_invocations { warmup_accumulator += operation(index); }
    black_box(warmup_accumulator);
    let mut durations_ns = Vec::with_capacity(sample_count);
    for _ in 0..sample_count {
        let start = Instant::now();
        let mut accumulator = 0.0;
        for index in 0..sample_invocations { accumulator += operation(index); }
        let duration = start.elapsed().as_nanos().max(1);
        black_box(accumulator);
        durations_ns.push(duration);
    }
    ResultRow { id, status: "supported", reason: "",
        warmup_operations: warmup_invocations * operations_per_invocation,
        operations_per_sample: sample_invocations * operations_per_invocation,
        durations_ns, oracle: Some(expected) }
}

fn unsupported(id: &'static str, reason: &'static str) -> ResultRow {
    ResultRow { id, status: "unsupported", reason, warmup_operations: 0,
        operations_per_sample: 0, durations_ns: Vec::new(), oracle: None }
}

fn batch_motor<const N: usize>(profile: &str, id: &'static str) -> ResultRow {
    let first = Motor::from(Translator::from_displacement(1.0, 2.0, 3.0));
    let second = Motor::from(Translator::from_displacement(-0.5, 0.25, 1.5));
    let left = BatchMotorSoA::<N>::from_slice(&vec![first; N]);
    let right = BatchMotorSoA::<N>::from_slice(&vec![second; N]);
    let invocations = if profile == "smoke" { 1 } else { 16_384 / N as u64 };
    let warmups = if profile == "smoke" { 1 } else { 4_096 / N as u64 };
    let samples = if profile == "smoke" { 3 } else { 15 };
    measure(id, 1.0, warmups.max(1), invocations.max(1), N as u64, samples, |index| {
        let result = if index & 1 == 0 { black_box(&left).compose(black_box(&right)) }
                     else { black_box(&right).compose(black_box(&left)) };
        black_box(result.blades[0][0])
    })
}

fn batch_point<const N: usize>(profile: &str, id: &'static str) -> ResultRow {
    let motor = Motor::from(Translator::from_displacement(1.0, 2.0, 3.0));
    let points = BatchPointSoA::<N>::from_slice(&vec![Point::new(2.5, -1.5, 4.0); N]);
    let invocations = if profile == "smoke" { 1 } else { 16_384 / N as u64 };
    let warmups = if profile == "smoke" { 1 } else { 4_096 / N as u64 };
    let samples = if profile == "smoke" { 3 } else { 15 };
    measure(id, 3.5, warmups.max(1), invocations.max(1), N as u64, samples, |_| {
        let result = black_box(&points).transform(black_box(&motor));
        black_box(result.x[0])
    })
}

fn orthogonal_operands() -> (OrthogonalMultivector32, OrthogonalMultivector32) {
    let blades: Vec<usize> = (0..32).collect();
    let left = OrthogonalMultivector32::from_blades(&blades, &[1.0; 32]);
    let mut right = left;
    right.set(0, 2.0);
    (left, right)
}

fn corrected_jacobian_checksum(chain: &KinematicChain, angles: &[f64]) -> f64 {
    let mut prefix = Motor::identity();
    let mut checksum = 0.0;
    for (index, joint) in chain.joints.iter().enumerate() {
        let frame = prefix.compose(&joint.origin_transform);
        let generator = joint.compute_generator();
        let column = generator.mv.sandwich_product(&frame.to_multivector());
        checksum += column.get(gafro::algebra::blades::E12)
            + column.get(gafro::algebra::blades::E13)
            + column.get(gafro::algebra::blades::E23)
            + column.get(gafro::algebra::blades::E1I)
            + column.get(gafro::algebra::blades::E2I)
            + column.get(gafro::algebra::blades::E3I);
        let q = angles.get(index).copied().unwrap_or(0.0);
        prefix = prefix.compose(&joint.compute_motor(q));
    }
    checksum
}

fn durations_json(values: &[u128]) -> String {
    values.iter().map(u128::to_string).collect::<Vec<_>>().join(",")
}

fn row_json(row: &ResultRow, p: &Provenance) -> String {
    let identity = format!("\"implementation\":{{\"family\":\"rust\",\"name\":\"gafro-rust\",\"repository_revision\":\"{}\",\"dirty\":{},\"compiler\":\"{}\",\"backend\":\"cpu-release\",\"flags\":[\"target: {}\",\"features: default\",\"profile: release\",\"codegen-units: 1\",\"lto: fat\",\"RUSTFLAGS: {}\"]}}", p.revision, p.dirty, p.compiler, p.target, p.flags);
    let host = row.id.split("/n").nth(1).and_then(|value| value.split('/').next())
        .and_then(|value| value.parse::<u64>().ok())
        .map(|batch| format!("{{\"clock\":\"std::time::Instant\",\"threads\":1,\"simd\":\"compiler-target\",\"alignment\":\"native\",\"batch_size\":{batch},\"layout\":\"structure-of-arrays\",\"packing\":\"excluded\",\"allocation\":\"excluded\",\"output_validation\":\"all_lanes\"}}"))
        .unwrap_or_else(|| "{\"clock\":\"std::time::Instant\"}".to_owned());
    match row.oracle {
        Some(oracle) => format!("{{\"schema_version\":\"gafro-benchmark-result/v1\",{},\"host\":{},\"workload_id\":\"{}\",\"status\":\"supported\",\"reason\":\"\",\"warmup_operations\":{},\"operations_per_sample\":{},\"sample_durations_ns\":[{}],\"oracle\":{{\"value\":{}}}}}", identity, host, row.id, row.warmup_operations, row.operations_per_sample, durations_json(&row.durations_ns), oracle),
        None => format!("{{\"schema_version\":\"gafro-benchmark-result/v1\",{},\"host\":{{}},\"workload_id\":\"{}\",\"status\":\"{}\",\"reason\":\"{}\"}}", identity, row.id, row.status, row.reason),
    }
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let profile = argument(&args, "--profile", "full");
    let provenance = Provenance {
        revision: argument(&args, "--revision", "unknown"),
        dirty: argument(&args, "--dirty", "false") == "true",
        compiler: argument(&args, "--compiler", "rustc unknown"),
        target: argument(&args, "--target", "unknown"),
        flags: argument(&args, "--rustflags", "none"),
    };
    let warmups = if profile == "smoke" { 8 } else { 1_000 };
    let operations = if profile == "smoke" { 1_000 } else { 10_000 };
    let samples = if profile == "smoke" { 3 } else { 15 };
    let first_motor = Motor::from(Translator::from_displacement(1.0, 2.0, 3.0));
    let second_motor = Motor::from(Translator::from_displacement(-0.5, 0.25, 1.5));
    let first_point = Point::new(2.5, -1.5, 4.0);
    let second_point = Point::new(3.0, 2.0, -1.0);
    let outer_left = [Point::new(1.0, 0.0, 0.0), Point::new(1.125, 0.0, 0.0)];
    let outer_right = [Point::new(0.0, 1.0, 0.0), Point::new(0.0, 1.0 / 1.125, 0.0)];
    let robotics_frame = Motor::from(Translator::from_displacement(0.0, 1.0, 0.0));
    let mut robotics_chain = KinematicChain::new();
    robotics_chain.add_joint(Joint::revolute([0.0, 0.0, 1.0], robotics_frame));
    robotics_chain.add_joint(Joint::revolute([0.0, 0.0, 1.0], robotics_frame));
    let robotics_positions = [[0.0, std::f64::consts::FRAC_PI_2],
        [1.0 / 1024.0, std::f64::consts::FRAC_PI_2 - 1.0 / 1024.0]];
    let robotics_oracle_motor = robotics_chain.forward_kinematics(&robotics_positions[0]);
    let robotics_expected_motor = [std::f64::consts::FRAC_1_SQRT_2, -std::f64::consts::FRAC_1_SQRT_2,
        0.0, 0.0, -std::f64::consts::FRAC_1_SQRT_2, -std::f64::consts::FRAC_1_SQRT_2, 0.0, 0.0];
    for (actual, expected) in robotics_oracle_motor.blades.iter().zip(robotics_expected_motor) {
        require_close("robotics FK coefficient", *actual, expected);
    }
    let (orthogonal_left, orthogonal_right) = orthogonal_operands();
    let mut rows = vec![unsupported("dense_geometric_product/f64/scalar",
        "legacy contract ID does not declare the orthogonal basis; use the explicit orthogonal variants"),
        measure("dense_geometric_product/f64/orthogonal", 1.0,
        warmups, operations, 1, samples, |_| {
            (black_box(&orthogonal_left).clone() * black_box(&orthogonal_right).clone()).scalar()
        })];
    rows.push(measure("dense_geometric_product/f64/orthogonal_conversion", 1.0,
        warmups, operations, 1, samples, |_| {
            let left = black_box(&orthogonal_left).to_null_basis();
            let right = black_box(&orthogonal_right).to_null_basis();
            let result = &left * &right;
            OrthogonalMultivector32::from_null_basis(&result).scalar()
        }));
    rows.push(measure("motor_composition_gp/f64/scalar", 1.0, warmups, operations, 1, samples, |i| {
        let result = if i & 1 == 0 { black_box(&first_motor).compose(black_box(&second_motor)) }
                     else { black_box(&second_motor).compose(black_box(&first_motor)) };
        black_box(result.scalar())
    }));
    rows.push(measure("sandwich_point_transform/f64/e1", 3.5, warmups, operations, 1, samples, |i| {
        let result = if i & 1 == 0 { black_box(&first_motor).apply(black_box(&first_point)) }
                     else { black_box(&second_motor).apply(black_box(&second_point)) };
        black_box(result.x())
    }));
    rows.push(measure("point_pair_outer_product/f64/e12", 1.0, warmups, operations, 1, samples, |i| {
        let lane = (i & 1) as usize;
        let result = black_box(&outer_left[lane].mv).outer_product(black_box(&outer_right[lane].mv));
        black_box(result.get(E12))
    }));
    rows.push(measure("rotor_construction/f64/scalar", std::f64::consts::FRAC_1_SQRT_2,
        warmups, operations, 1, samples, |_| {
            let rotor = Rotor::from_axis_angle(0.0, 0.0, 1.0, std::f64::consts::FRAC_PI_2);
            rotor.scalar()
        }));
    rows.push(measure("translator_construction/f64/e1i", -0.5, warmups, operations, 1, samples, |_| {
        let translator = Translator::from_displacement(1.0, 2.0, 3.0);
        require_close("translator construction e2i", translator.blades[2], -1.0);
        require_close("translator construction e3i", translator.blades[3], -1.5);
        translator.blades[1]
    }));
    rows.push(measure("robotics_forward_kinematics_2r/f64/motor_checksum", -std::f64::consts::SQRT_2,
        warmups, operations, 1, samples, |i| {
            let motor = black_box(&robotics_chain).forward_kinematics(black_box(&robotics_positions[(i & 1) as usize]));
            black_box(motor.blades.iter().sum())
        }));
    rows.push(measure("robotics_geometric_jacobian_2r/f64/base_checksum", 5.0,
        warmups, operations, 1, samples, |i| {
            corrected_jacobian_checksum(&robotics_chain, &robotics_positions[(i & 1) as usize])
        }));
    rows.push(batch_motor::<16>(&profile, "batch_motor_composition/f64/n16/scalar_lane0"));
    rows.push(batch_motor::<256>(&profile, "batch_motor_composition/f64/n256/scalar_lane0"));
    rows.push(batch_motor::<4096>(&profile, "batch_motor_composition/f64/n4096/scalar_lane0"));
    rows.push(batch_point::<16>(&profile, "batch_point_transform/f64/n16/e1_lane0"));
    rows.push(batch_point::<256>(&profile, "batch_point_transform/f64/n256/e1_lane0"));
    rows.push(batch_point::<4096>(&profile, "batch_point_transform/f64/n4096/e1_lane0"));
    let json = rows.iter().map(|row| row_json(row, &provenance)).collect::<Vec<_>>().join(",");
    println!("{{\"results\":[{json}]}}");
}
