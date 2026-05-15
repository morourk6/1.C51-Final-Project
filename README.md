# 1.C51-Final-Project - Predicting Life of Mine with Open-Source Data

### [Main data source  - Jasansky et al] (https://www.nature.com/articles/s41597-023-01965-y)

This is our work for the ML for Sustainable Systems class final project - Spring 2026. Our goal was to try to predict Life of Mine, which is the amount of years a mine is operational for, with relevant features such as the price of the commodity, the country location, and the reserve value. 

## File Description

Most of our work was parallelized on data processing. It can be found in the following files: 

- `ananda_data` includes data exploration and processing commodity prices
- `data_processing_final` (final is usually a bad omen, as we have discovered)
- `data_processing_final2`
- `Reese_data_processing`

Our many data and input/output files are in `data/`, with the key final files being `for_loop_data` and its many variations to fit out different models on yearly values, as well as `average_data` which combines all years into one.

Our actual models are divided into two files which were created more collaboratively:

- `rf_model` includes the vast majority of our model attempts and exploration, particularly for the Random Forest Regressor
- `rf_bins` includes our Random Forest Classifier and the code we used to understand the spread of our data and its division into quintiles

We would recommend starting on `rf_model` and `rf_bins` to understand our main model, and go through the data processing files as needed to see how we made the information we received from open source data into a system "understandable" for our model, including one-hot encoding key categorical variables.


