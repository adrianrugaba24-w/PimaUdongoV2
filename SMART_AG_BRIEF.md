# SMART-AG: brief for the agent

Source: "SMART-AG: A Precision Agriculture AI-Powered Edge Computing System", Tobit Kabuya Bushenyula (S22B23/001), BSc Computer Science project report, Uganda Christian University, April 2025. Supervisor: Mr. Ian Raymond Osolo.

Only the PDF has been seen. The code, datasets and hardware are not available. Statements marked INFERENCE are readings, not stated in the report. Verify any figure against the PDF before quoting it.

## 1. What it is

A built, offline device that reads soil sensors on a Raspberry Pi, classifies soil quality, recommends a crop, and sends a farmer a daily SMS at 6:30 AM. It needs mobile network coverage for SMS but no internet.

Target users: smallholder farmers in rural Africa with basic phones, and home gardeners. It was tried informally on a small group of agriculture students.

## 2. Problem and objectives (as stated)

Problem: food insecurity in Africa (296 million people facing hunger in 2023, per the report), low technology adoption among smallholder farmers, and tools that need internet or are too complex.

Objectives:
1. Analyse soil health and recommend crops from nutrient levels.
2. Suggest nutrients or fertilisers to improve fertility.
3. Process and store data locally on the device.
4. Deliver advice by SMS without internet.
5. Test the system in real-world conditions and measure its effect on productivity.

Objective 5 is not evidenced in the report. No yield or productivity measurement appears.

## 3. How it works

1. NPK 7-in-1 sensor (model NPKPHCTH-S, RS485 output) reads nitrogen, phosphorus, potassium, pH, electrical conductivity, soil temperature and moisture.
2. An RS485-to-TTL USB converter passes readings to a Raspberry Pi 4 Model B. A smaller converter was incompatible, so the older USB one was used.
3. The Pi logs timestamped readings to a local CSV file.
4. Two machine-learning classifiers run on the Pi:
   - Soil quality: Poor, Average or Good. The notebook shows `LGBMClassifier`.
   - Crop recommendation: best crop plus alternatives. The notebook variable is `model_1`, and the algorithm is not named.
5. Advice text is attached by soil-quality class. The data flow diagram shows one branch of "tailored actionable insights" per class. INFERENCE: this is probably fixed or rule-based text, not a learned model. The report does not say.
6. A SIM800L GSM module sends the SMS to one predefined phone number. The report also writes "GSM800L" in places.

Power: the prototype used the Pi's 5V adapter. A 7-12V rechargeable battery and a waterproof recycled-plastic enclosure ("SMART-AG Box") are concept only.

Software: Python, Jupyter Notebook for model development, Raspberry Pi OS with scheduled scripts.

## 4. Sample SMS (as shown)

A greeting, a quality statement ("your soil conditions look good for farming"), the seven sensor values (for example pH 5.9, temperature 25.7, humidity 49.9, conductivity 876, N 144, P 379, K 374), an ideal crop (grapes) with alternatives (orange, apple), and a soil quality word ("Great"). No units are shown for any value. The stated quality labels (Poor, Average, Good) differ from the word in the sample ("Great").

## 5. Evidence the report gives

| Item | Reported |
|---|---|
| Soil quality model score | 1.0 on train and 1.0 on test (notebook screenshot) |
| Crop model score | 0.9987 train, 0.9909 test |
| System test | About 2 weeks running, daily SMS sent, CSV logged |
| Weather charts | Soil temperature falling and humidity rising around 16 March 2025, presented as the system "detecting climate change" |
| User acceptance | Informal feedback from agriculture students on clarity, helpfulness and timeliness; no numbers |
| Stakeholder feedback | Tailor SMS to crop stage, prefer actions over raw data, study affordability, use African data, document the project, consider patent protection |

The report does not describe the source or labelling of the datasets, the train/test split method, or any baseline.

## 6. Limitations the report admits

Hardware incompatibility, foreign datasets adapted to Africa (it produced crops uncommon in Africa), partial automation with delays and errors, patchy SMS delivery in remote areas, single user and single phone number, low budget, no long-term field testing, and no solar or off-grid power.

## 7. Reviewer observations (INFERENCE, my reading)

- A score of 1.0 on both train and test, from a single split, is a red flag: possible leakage, labels derived as a rule from the same inputs, or an easy dataset. It says nothing about performance on new fields.
- No cross-validation, group or spatial split, baseline, or sensor-noise test is reported.
- Sensor accuracy is described as confirmed but no reference measurement or error figure is given.
- Fertiliser and compost advice is not validated against soil lab tests or yields. Claims of higher yield, less waste and saved labour are not measured.
- The humidity chart rises (about 22 to 42) but its caption says "considerable drop". The temperature chart does fall.
- Two weeks of temperature and humidity trends show a weather change the sensor registered. They are not evidence of detecting climate change.
- The literature review mentions voice features that were not built. Offline operation is described as implemented and again as a future recommendation.
- "Soil health" is used for what the model classifies, which is a quality label, not a measured health index.

## 8. How to use this brief

- Treat SMART-AG as a completed end-to-end prototype with light evaluation, not as a validated method.
- Cite it factually. It reports single held-out-split scores and has no spatial validation or sensor-error analysis. Do not call it wrong or fake.
- Do not assume its data, code or hardware exist in this workspace.
- Its accuracy scores (classification) are not comparable with regression R2 or with any spatial cross-validation result.
- Do not copy its language ("soil health", "accurate", "reliable", "actionable") into other project documents without checking those documents' own copy rules.
