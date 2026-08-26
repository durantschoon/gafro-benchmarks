module Main

import Gafro.Algebra.Blade
import Gafro.Algebra.Multivector
import Gafro.Algebra.Products
import Gafro.Core
import Gafro.Conformal.Euclidean
import Gafro.Conformal.Objects
import Gafro.Conformal.Versor
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

resultJSON : Provenance -> Nat -> Nat -> Measurement -> String
resultJSON provenance warmups operations measurement =
  "{\"schema_version\":\"gafro-benchmark-result/v1\"," ++
  "\"implementation\":{\"family\":\"idris2\",\"name\":\"gafro-idris2\"," ++
  "\"repository_revision\":\"" ++ provenance.revision ++ "\"," ++
  "\"dirty\":" ++ boolJSON provenance.dirty ++ "," ++
  "\"compiler\":\"" ++ provenance.compiler ++ "\",\"backend\":\"" ++ provenance.backend ++ "\"," ++
  "\"flags\":[\"generated-c-compiler: " ++ provenance.cCompiler ++ "\",\"generated-c-flags: " ++ provenance.cFlags ++ "\"]}," ++
  "\"host\":{\"clock\":\"System.Clock.Monotonic\"}," ++
  "\"workload_id\":\"" ++ measurement.workloadId ++ "\",\"status\":\"supported\",\"reason\":\"\"," ++
  "\"warmup_operations\":" ++ show warmups ++ ",\"operations_per_sample\":" ++ show operations ++ "," ++
  "\"sample_durations_ns\":" ++ integersJSON measurement.durations ++ "," ++
  "\"oracle\":{\"value\":" ++ show measurement.oracle ++ "}}"

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
  putStrLn ("{\"results\":[" ++ joinBy "," (map (resultJSON provenance warmups operations) [dense, composition, transform, outer]) ++ "]}")
