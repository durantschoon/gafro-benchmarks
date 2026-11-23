module Main

import Gafro.Algebra.Blade
import Gafro.Algebra.Multivector
import Gafro.Algebra.Products
import Gafro.Core
import Gafro.Conformal.Euclidean
import Gafro.Conformal.Objects
import Gafro.Conformal.Versor
import Gafro.Robotics.Kinematics
import Gafro.Robotics.Physics
import Data.Fin
import Data.Maybe
import Data.String
import Data.Vect
import System
import System.Clock

%default total

record Provenance where
  constructor MkProvenance
  revision : String
  dirty : Bool
  compiler : String
  backend : String
  cCompiler : String
  cFlags : String

record Measurement where
  constructor MkMeasurement
  workloadId : String
  durations : List Integer
  oracle : Double

denseLeft : Multivector
denseLeft = fromCoeffs (replicate 32 1.0)

denseRight : Multivector
denseRight = fromCoeffs
  [ 2.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0
  , 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0
  , 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0
  , 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0
  ]

denseGeometricProduct : Bool -> Double
denseGeometricProduct first =
  if first
     then coeff scalarBlade (geo denseLeft denseRight)
     else coeff scalarBlade (geo denseRight denseLeft)

translation : Bool -> Vec3
translation first = if first
                   then MkVec3 1.0 2.0 3.0
                   else MkVec3 (-0.5) 0.25 1.5

point : Bool -> Vec3
point first = if first
             then MkVec3 2.5 (-1.5) 4.0
             else MkVec3 3.0 2.0 (-1.0)

firstMotor : Versor Trans
firstMotor = translator (translation True)

secondMotor : Versor Trans
secondMotor = translator (translation False)

rotorConstruction : Bool -> Double
rotorConstruction _ =
  case unitBivector 1.0e-12 (MkEuclideanBivector 0.0 0.0 1.0) of
    Right axis => coeff scalarBlade (Versor.mv (rotor axis (pi / 2.0)))
    Left _ => 0.0

firstPoint : Point
firstPoint = up (point True)

secondPoint : Point
secondPoint = up (point False)

outerA0 : Multivector
outerA0 = Point.mv (up (MkVec3 1.0 0.0 0.0))

outerB0 : Multivector
outerB0 = Point.mv (up (MkVec3 0.0 1.0 0.0))

outerA1 : Multivector
outerA1 = Point.mv (up (MkVec3 1.125 0.0 0.0))

outerB1 : Multivector
outerB1 = Point.mv (up (MkVec3 0.0 (1.0 / 1.125) 0.0))

motorComposition : Bool -> Double
motorComposition first =
  if first
     then coeff scalarBlade (Versor.mv (compose firstMotor secondMotor))
     else coeff scalarBlade (Versor.mv (compose secondMotor firstMotor))

pointTransform : Bool -> Double
pointTransform first =
  let transformed = if first
                       then Point.apply firstMotor firstPoint
                       else Point.apply secondMotor secondPoint
  in coeff e1Blade (Point.mv transformed)

pointPairOuter : Bool -> Double
pointPairOuter first =
  if first
     then coeff (MkBlade 3) (wedge outerA0 outerB0)
     else coeff (MkBlade 3) (wedge outerA1 outerB1)

roboticsAxis : Either NormalizeError UnitBivector
roboticsAxis = unitBivector 1.0e-12 (MkEuclideanBivector 0.0 0.0 1.0)

roboticsChain : UnitBivector -> KinematicChain 2
roboticsChain axis = MkKinematicChain
  [ revoluteJoint axis (MkVec3 0.0 1.0 0.0)
  , revoluteJoint axis (MkVec3 0.0 1.0 0.0)
  ]

roboticsAngles : Bool -> Vect 2 Scalar
roboticsAngles first = if first
                       then [0.0, pi / 2.0]
                       else [0.0009765625, (pi / 2.0) - 0.0009765625]

roboticsMotorChecksum : Bool -> Double
roboticsMotorChecksum first =
  case roboticsAxis of
    Right bZ =>
      let motor = Versor.mv (forwardKinematics (roboticsChain bZ) (roboticsAngles first))
      in coeff scalarBlade motor
         + coeff (MkBlade 3) motor + coeff (MkBlade 5) motor
         + coeff (MkBlade 6) motor + coeff (MkBlade 17) motor
         + coeff (MkBlade 18) motor + coeff (MkBlade 20) motor
         + coeff (MkBlade 23) motor
    Left _ => 0.0

axisChecksum : Multivector -> Double
axisChecksum value = coeff (MkBlade 6) value + coeff (MkBlade 5) value
                    + coeff (MkBlade 3) value + coeff (MkBlade 17) value
                    + coeff (MkBlade 18) value + coeff (MkBlade 20) value

axisMatches : Multivector -> List Double -> Bool
axisMatches value [a, b, c, d, e, f] =
  abs (coeff (MkBlade 3) value - a) <= 1.0e-10
  && abs (coeff (MkBlade 5) value - b) <= 1.0e-10
  && abs (coeff (MkBlade 6) value - c) <= 1.0e-10
  && abs (coeff (MkBlade 17) value - d) <= 1.0e-10
  && abs (coeff (MkBlade 18) value - e) <= 1.0e-10
  && abs (coeff (MkBlade 20) value - f) <= 1.0e-10
axisMatches _ _ = False

roboticsJacobianOracle : Bool -> Bool
roboticsJacobianOracle first =
  case roboticsAxis of
    Right bZ =>
      case spatialAxes (roboticsChain bZ) (roboticsAngles first) of
        [firstAxis, secondAxis] =>
          axisMatches firstAxis [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
          && axisMatches secondAxis [1.0, 0.0, 0.0, 2.0, 0.0, 0.0]
        _ => False
    Left _ => False

roboticsJacobianChecksum' : Either NormalizeError UnitBivector -> Bool -> Double
roboticsJacobianChecksum' (Right bZ) first =
  sum (map axisChecksum (spatialAxes (roboticsChain bZ) (roboticsAngles first)))
roboticsJacobianChecksum' (Left _) first = 0.0

roboticsJacobianChecksum : Bool -> Double
roboticsJacobianChecksum first =
  roboticsJacobianChecksum' roboticsAxis first

physicsInertia : SpatialInertia
physicsInertia = MkSpatialInertia
  [ [2.0, 0.0, 0.0, 0.0, 0.0, 0.0]
  , [0.0, 2.0, 0.0, 0.0, 0.0, 0.0]
  , [0.0, 0.0, 0.8, 0.0, 0.0, 0.0]
  , [0.0, 0.0, 0.0, 2.0, 0.0, 0.0]
  , [0.0, 0.0, 0.0, 0.0, 0.5, 0.0]
  , [0.0, 0.0, 0.0, 0.0, 0.0, 0.5]
  ]

physicsTwist : Twist
physicsTwist = twist 0.1 0.2 0.3 1.0 2.0 3.0

||| The f1-row, v1-column entry of the inertia transformed by the C++ adapter's
||| motors[0] (a pure translation by (1, 2, 3)). gafro-cpp's observable is
||| `transform(motor).getElement01().get<e01>()`: the element in wrench slot e01
||| (f1), read at the coefficient that its inner product pairs with the twist's
||| e1i (v1) slot. In gafro-idris2's (f1, f2, tau12, f3, tau13, tau23) x
||| (v1, v2, w12, v3, w13, w23) matrix that is row 0, column 0.
inertiaTransformE01 : Bool -> Double
inertiaTransformE01 _ =
  case transformInertia physicsInertia firstMotor of
    MkSpatialInertia rows => index 0 (index 0 rows)

||| The e1i coefficient of `translator (1, 2, 3)`. In gafro-idris2's orthogonal
||| encoding `e1 ∧ nInf` is `e1∧ePlus + e1∧eMinus` (masks 9 and 17), each
||| carrying the e1i coefficient, so the reading averages both blades.
translatorE1i : Multivector -> Double
translatorE1i value = 0.5 * (coeff (MkBlade 9) value + coeff (MkBlade 17) value)

translatorConstruction : Bool -> Double
translatorConstruction _ = translatorE1i (Versor.mv (translator (translation True)))

||| Untimed check of every translator coefficient the C++ adapter checks: both
||| blades of each null pair agree, and (e1i, e2i, e3i) = (-0.5, -1.0, -1.5).
translatorOracle : Bool
translatorOracle =
  let value = Versor.mv (translator (translation True))
      pairs : List (Fin 32, Fin 32, Double)
      pairs = [(9, 17, -0.5), (10, 18, -1.0), (12, 20, -1.5)]
  in all (\(plus, minus, expected) =>
            abs (coeff (MkBlade plus) value - expected) <= 1.0e-10
            && abs (coeff (MkBlade minus) value - expected) <= 1.0e-10) pairs
     && abs (coeff scalarBlade value - 1.0) <= 1.0e-10

||| The full-tensor workload's mass and rotational tensor entries (the
||| tensor's own entries, not negated products of inertia).
fullTensorMass, fullIxx, fullIxy, fullIxz, fullIyy, fullIyz, fullIzz : Double
fullTensorMass = 2.0
fullIxx = 0.5
fullIxy = 0.05
fullIxz = 0.02
fullIyy = 0.6
fullIyz = 0.03
fullIzz = 0.8

||| The 6x6 matrix for the full-tensor workload, written by this adapter (not
||| by gafro-idris2) from the contract convention. Rows are wrench coordinates
||| (f1, f2, tau12, f3, tau13, tau23); columns are twist coordinates
||| (v1, v2, w12, v3, w13, w23). With omega = (w23, -w13, w12) and tau = I omega,
||| tau12 = tau_z, tau13 = -tau_y and tau23 = tau_x, which gives the signed
||| bivector-basis block below.
fullTensorInertia : SpatialInertia
fullTensorInertia = MkSpatialInertia
  [ [fullTensorMass, 0.0, 0.0, 0.0, 0.0, 0.0]
  , [0.0, fullTensorMass, 0.0, 0.0, 0.0, 0.0]
  , [0.0, 0.0, fullIzz, 0.0, -fullIyz, fullIxz]
  , [0.0, 0.0, 0.0, fullTensorMass, 0.0, 0.0]
  , [0.0, 0.0, -fullIyz, 0.0, fullIyy, -fullIxy]
  , [0.0, 0.0, fullIxz, 0.0, -fullIxy, fullIxx]
  ]

fullTensorExpected : Vect 6 Double
fullTensorExpected = [2.0, 4.0, 0.08, 6.0, 0.102, 0.142]

fullTensorObserved : Vect 6 Double
fullTensorObserved = wrenchCoords (applyInertia fullTensorInertia physicsTwist)

fullTensorWrenchChecksum : Bool -> Double
fullTensorWrenchChecksum _ =
  let w = applyInertia fullTensorInertia physicsTwist
  in w.f1 + w.f2 + w.tau12 + w.f3 + w.tau13 + w.tau23

fullTensorOracle : Bool
fullTensorOracle =
  all id (zipWith (\actual, expected => abs (actual - expected) <= 1.0e-10) fullTensorObserved fullTensorExpected)
  && abs (sum fullTensorObserved - 12.324) <= 1.0e-10

physicsWrenchChecksum : Bool -> Double
physicsWrenchChecksum _ =
  let w = applyInertia physicsInertia physicsTwist
  in w.f1 + w.f2 + w.tau12 + w.f3 + w.tau13 + w.tau23

runOperations : (Bool -> Double) -> Bool -> Nat -> Double -> Double
runOperations operation first Z accumulator = accumulator
runOperations operation first (S remaining) accumulator =
  runOperations operation (not first) remaining (accumulator + operation first)

warm : (Bool -> Double) -> Nat -> IO ()
warm operation count = do
  let observed = runOperations operation True count 0.0
  if observed == observed then pure () else pure ()

covering
timedSample : (Bool -> Double) -> Nat -> IO (Integer, Double)
timedSample operation count = do
  start <- clockTime Monotonic
  let observed = runOperations operation True count 0.0
  stop <- clockTime Monotonic
  pure (toNano stop - toNano start, observed)

covering
samples : (Bool -> Double) -> Nat -> Nat -> IO (List Integer)
samples operation operations Z = pure []
samples operation operations (S remaining) = do
  (duration, observed) <- timedSample operation operations
  rest <- samples operation operations remaining
  if observed == observed then pure (duration :: rest) else pure (duration :: rest)

close : Double -> Double -> Bool
close actual expected = abs (actual - expected) <= 1.0e-10

covering
measure : String -> Double -> (Bool -> Double) -> Nat -> Nat -> Nat -> IO Measurement
measure workload expected operation warmups operations sampleCount = do
  let actual = operation True
  if close actual expected
     then do
       warm operation warmups
       timings <- samples operation operations sampleCount
       pure (MkMeasurement workload timings actual)
     else do
       putStrLn ("oracle mismatch for " ++ workload ++ ": expected " ++ show expected ++ ", got " ++ show actual)
       exitFailure

boolJSON : Bool -> String
boolJSON True = "true"
boolJSON False = "false"

integersJSON : List Integer -> String
integersJSON values = "[" ++ joinBy "," (map show values) ++ "]"

||| The implementation object, with any row-specific flags appended.
implementationJSON : Provenance -> List String -> String
implementationJSON provenance extraFlags =
  "\"implementation\":{\"family\":\"idris2\",\"name\":\"gafro-idris2\"," ++
  "\"repository_revision\":\"" ++ provenance.revision ++ "\"," ++
  "\"dirty\":" ++ boolJSON provenance.dirty ++ "," ++
  "\"compiler\":\"" ++ provenance.compiler ++ "\",\"backend\":\"" ++ provenance.backend ++ "\"," ++
  "\"flags\":[" ++ joinBy "," (map (\flag => "\"" ++ flag ++ "\"")
      (["generated-c-compiler: " ++ provenance.cCompiler, "generated-c-flags: " ++ provenance.cFlags] ++ extraFlags)) ++ "]}"

resultJSONWithFlags : Provenance -> List String -> Nat -> Nat -> Measurement -> String
resultJSONWithFlags provenance extraFlags warmups operations measurement =
  "{\"schema_version\":\"gafro-benchmark-result/v1\"," ++
  implementationJSON provenance extraFlags ++ "," ++
  "\"host\":{\"clock\":\"System.Clock.Monotonic\"}," ++
  "\"workload_id\":\"" ++ measurement.workloadId ++ "\",\"status\":\"supported\",\"reason\":\"\"," ++
  "\"warmup_operations\":" ++ show warmups ++ ",\"operations_per_sample\":" ++ show operations ++ "," ++
  "\"sample_durations_ns\":" ++ integersJSON measurement.durations ++ "," ++
  "\"oracle\":{\"value\":" ++ show measurement.oracle ++ "}}"

resultJSON : Provenance -> Nat -> Nat -> Measurement -> String
resultJSON provenance = resultJSONWithFlags provenance []

||| A row whose untimed oracle check failed: evidence, not a crash.
failedJSON : Provenance -> List String -> String -> String -> String
failedJSON provenance extraFlags reason workload =
  "{\"schema_version\":\"gafro-benchmark-result/v1\"," ++
  implementationJSON provenance extraFlags ++ "," ++
  "\"host\":{},\"workload_id\":\"" ++ workload ++ "\",\"status\":\"failed\"," ++
  "\"reason\":\"" ++ reason ++ "\"}"

fullTensorFlags : List String
fullTensorFlags =
  [ "inertia-matrix: 6x6 matrix written by the adapter from the contract tensor and convention, not built by gafro-idris2; the library supplies applyInertia" ]

unsupportedJSONWithReason : Provenance -> String -> String -> String
unsupportedJSONWithReason provenance reason workload =
  "{\"schema_version\":\"gafro-benchmark-result/v1\"," ++
  implementationJSON provenance [] ++ "," ++
  "\"host\":{},\"workload_id\":\"" ++ workload ++ "\",\"status\":\"unsupported\"," ++
  "\"reason\":\"" ++ reason ++ "\"}"

unsupportedJSON : Provenance -> String -> String
unsupportedJSON provenance = unsupportedJSONWithReason provenance "gafro-idris2 exposes no CPU SoA batch API"

valueAfter : String -> List String -> Maybe String
valueAfter key (candidate :: value :: rest) = if candidate == key then Just value else valueAfter key (value :: rest)
valueAfter key _ = Nothing

argument : String -> String -> List String -> String
argument key fallback arguments = fromMaybe fallback (valueAfter key arguments)

covering
main : IO ()
main = do
  arguments <- getArgs
  let profile = argument "--profile" "full" arguments
      warmups : Nat
      warmups = if profile == "smoke" then 8 else 1000
      operations : Nat
      operations = if profile == "smoke" then 1000 else 10000
      sampleCount : Nat
      sampleCount = if profile == "smoke" then 3 else 15
      provenance = MkProvenance
        (argument "--revision" "unknown" arguments)
        (argument "--dirty" "false" arguments == "true")
        (argument "--compiler" "Idris 2 unknown" arguments)
        (argument "--backend" "refc" arguments)
        (argument "--c-compiler" "unknown" arguments)
        (argument "--c-flags" "unknown" arguments)
  dense <- measure "dense_geometric_product/f64/scalar" 1.0 denseGeometricProduct warmups operations sampleCount
  composition <- measure "motor_composition_gp/f64/scalar" 1.0 motorComposition warmups operations sampleCount
  transform <- measure "sandwich_point_transform/f64/e1" 3.5 pointTransform warmups operations sampleCount
  outer <- measure "point_pair_outer_product/f64/e12" 1.0 pointPairOuter warmups operations sampleCount
  rotor <- measure "rotor_construction/f64/scalar" (sqrt 0.5) rotorConstruction warmups operations sampleCount
  fk <- measure "robotics_forward_kinematics_2r/f64/motor_checksum" (-sqrt 2.0) roboticsMotorChecksum warmups operations sampleCount
  if roboticsJacobianOracle True
     then pure ()
     else do
       putStrLn "oracle mismatch for robotics_geometric_jacobian_2r/f64/base_checksum: full matrix"
       exitFailure
  jacobian <- measure "robotics_geometric_jacobian_2r/f64/base_checksum" 5.0 roboticsJacobianChecksum warmups operations sampleCount
  inertiaAction <- measure "spatial_inertia_action/f64/wrench_checksum" 12.33 physicsWrenchChecksum warmups operations sampleCount
  if translatorOracle
     then pure ()
     else do
       putStrLn "oracle mismatch for translator_construction/f64/e1i: translator coefficients"
       exitFailure
  translatorRow <- measure "translator_construction/f64/e1i" (-0.5) translatorConstruction warmups operations sampleCount
  inertiaTransform <- measure "spatial_inertia_transform/f64/e01_mass" 2.0 inertiaTransformE01 warmups operations sampleCount
  let fullTensorId = "spatial_inertia_action/f64/full_tensor_wrench_checksum"
  fullTensor <- if fullTensorOracle
     then do
       row <- measure fullTensorId 12.324 fullTensorWrenchChecksum warmups operations sampleCount
       pure (resultJSONWithFlags provenance fullTensorFlags warmups operations row)
     else pure (failedJSON provenance fullTensorFlags
       ("untimed oracle mismatch in gafro-idris2 applyInertia on the adapter-written full-tensor matrix: expected wrench coordinates (f1, f2, tau12, f3, tau13, tau23) "
         ++ show fullTensorExpected ++ ", observed " ++ show fullTensorObserved) fullTensorId)
  let supported = map (resultJSON provenance warmups operations) [dense, composition, transform, outer, rotor, translatorRow, inertiaAction, inertiaTransform] ++ [fullTensor]
      unsupported = map (unsupportedJSON provenance)
        [ "batch_motor_composition/f64/n16/scalar_lane0"
        , "batch_motor_composition/f64/n256/scalar_lane0"
        , "batch_motor_composition/f64/n4096/scalar_lane0"
        , "batch_point_transform/f64/n16/e1_lane0"
        , "batch_point_transform/f64/n256/e1_lane0"
        , "batch_point_transform/f64/n4096/e1_lane0"
        ]
      robotics = map (resultJSON provenance warmups operations) [fk, jacobian]
  putStrLn ("{\"results\":[" ++ joinBy "," (supported ++ robotics ++ unsupported) ++ "]}")
