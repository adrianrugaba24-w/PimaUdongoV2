# Pima

Sign in to check your soil.

Phone number or username Password

Each account has one role. Farmer accounts cannot open researcher pages.

PimaSoil carbon check

**Layout preview.** The sensor readings and the carbon estimate are simulated. Validation figures on researcher pages come from the project’s results run.

Less carbonThe shaded part shows where it could beMore carbon

### How much can you trust this check?

Based on tests on soils the check had not seen before.

### Your soil at a glance

Readings from your sensor, last updated .

### What to do now

Sampling tips are general and should be confirmed with your extension officer.

### Should I get a laboratory test?

Yes, if any of these is true:

- This check says it is not sure.
- You are about to spend money on lime, fertiliser or compost.
- A reading looks unusual, or jumps around between readings.
- Your crops are doing badly and you do not know why.

How to take a good soil sample

1. Use a clean spade or trowel. Clear away leaves and surface litter.
2. Dig a small hole about 20 cm deep and cut a thin slice from one side.
3. Repeat at 5 to 8 spots across the field. Avoid paths, field edges and places where compost or animals have been.
4. Mix the slices in a clean bucket and take about half a kilogram.
5. Put it in a clean bag, label it with your name, field and date, and take it to the laboratory soon.

General guidance. Confirm with your extension officer.

What your readings mean

Acidity (pH)

How acidic or alkaline the soil is. Most crops grow best in slightly acidic to neutral soil. Very acidic or very alkaline soil can lock up nutrients.

Salt level

How much dissolved salt is in the soil. Too much stops plants taking up water.

Moisture

How wet the soil is. It changes quickly after rain, so compare readings taken in similar conditions.

Temperature

It changes how fast living things in the soil work.

Who can help

- Your district agricultural officer
- A local extension worker or farmer group
- A university or research laboratory that tests soil

Ask: “Which test do you recommend for my crop? How should I collect and send the sample?”

### General practices that help soil carbon

Not based on your reading.

- **Leave crop residues on the field**\
  They feed the soil and hold moisture.
- **Mulch between rows**\
  It protects the surface from sun and rain.
- **Rotate with beans or groundnuts**\
  Their roots and leaves return carbon and nitrogen.
- **Add compost or manure where you can**\
  It adds organic matter to the topsoil.

Sources to be added before wider use.

### What is soil carbon?

The carbon held in your soil, mostly from plants and animals that have broken down. More carbon usually means soil that holds water and nutrients better.

### How sure are we?

Pima estimates carbon from your pH and salt readings and your soil type. We tested it on soils it had never seen, and it is often far off. So it tells you when it is not sure, and in that case you should get a laboratory test.

### What the sensor measures

Acidity (pH), salt level, moisture and temperature. Soil carbon cannot be read by a simple sensor, which is why we estimate it.

Spatial R² (random forest)**0.086**on areas it has not seen

Random-split R²**0.338**same model

Validation gap**0.252 ± 0.011**random minus spatial

Sensor tolerance**0.5 × spread**where it stops beating the average

### Random vs. spatial validation

R² by model

Random splitUnseen areas

### Sensor error budget

Simulated noise against the tolerance, as a multiple of each input’s spread

01 ×

Dashed line: random forest stops beating the field average. Measured error from a real sensor: not yet available.

### Are the ranges honest?

Share of held-out samples inside the 90% range

88.8% covered, against 90% targeted. Typical range width is 4.21 g/100 g, so most answers come out “too uncertain”.

### Models

Random forest is the one served by the app

| Model | R² random | R² spatial | RMSE spatial |
| --- | --- | --- | --- |
| Random forest | 0.338 | 0.086 | 1.339 |
| Gradient boosting | 0.295 | 0.078 | 1.344 |
| Field average | −0.002 | −0.030 | 1.421 |

### Simulated sensor node

A new reading arrives every 3 seconds. Noise is set in the preview controls below.

| Time | pH | Salt (dS/m) | Estimate | Answer |
| --- | --- | --- | --- | --- |

### How the model was built and tested

1. **Assemble.** 926 samples from 19 countries; pH and EC from CROPNUTS, texture and total carbon from ICRAF.
2. **Split.** Shuffled 5-fold baseline, and GroupKFold over 10 blocks of site coordinates.
3. **Train.** Five models, five seeds, tuning inside folds only.
4. **Evaluate.** R², RMSE and MAE pooled out-of-fold, on the original scale.
5. **Stress.** Gaussian noise on the inputs, from 0 to 1 × each input’s spread.
6. **Calibrate.** Split-conformal 90% range. A gate refuses to answer when it is too wide.

Final-year project, Department of Computing and Technology, Uganda Christian University. Not validated on field sensors or Ugandan farms.

### This page is not available for your account

Farmer accounts only see the plain-language result. Sign in as a researcher to see the evidence.

Design preview controls (not part of the product)

Acidity (pH): Salt (EC, dS/m): Sensor noise (× spread): Soil type [ ] Pretend the model were more precise (±0.4 instead of ±2.1)