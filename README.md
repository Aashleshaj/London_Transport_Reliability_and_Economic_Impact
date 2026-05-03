# London-Transport-Reliability-and-Economic-Impact-
Public transport delays, strikes, and infrastructure failures do not affect all areas equally. This project investigates whether transport unreliability disproportionately impacts commuters in outer boroughs (like Brent or Croydon) compared to central London, and correlates these delays with local economic data.

Data Collection
1. TfL Line Status — Manual Download 
   status_all.json --> https://api.tfl.gov.uk/Line/Mode/tube,overground,elizabeth-line,dlr/Status
   Tube status:
   tube_status.json -> https://api.tfl.gov.uk/Line/Mode/tube/Status
   overground status
   status.json -> https://api.tfl.gov.uk/Line/Mode/overground/Status
   Disturption 
   service_disturption.json -> https://api.tfl.gov.uk/Line/Mode/tube,overground/Status?detail=true

Official Source Links
TfL API
WhatOfficial SourceURLTfL API homepageTransport for London https://api.tfl.gov.ukTfL Open Data portalTransport for London https://tfl.gov.uk/info-for/open-data-usersTfL API documentationTransport for London https://api.tfl.gov.uk/swagger/ui/index.htmlTfL press releasesTransport for London https://tfl.gov.uk/info-for/media/press-releasesTfL performance reportsTransport for London https://tfl.gov.uk/corporate/publications-and-reports/underground-services-performance

ONS / Census Data
WhatOfficial SourceURLCensus 2021 custom dataOffice for National Statisticshttps://create.census.gov.uk/queryCensus TS058 distance to workONS Census 2021https://www.ons.gov.uk/datasets/TS058/editions/2021/versions/3Census TS061 method of travelONS Census 2021https://www.ons.gov.uk/datasets/TS061/editions/2021/versions/3National Travel SurveyDept for Transporthttps://www.gov.uk/government/collections/national-travel-survey-statistics

London Data
WhatOfficial SourceURLLondon Datastore (GLA)Greater London Authority
https://data.london.gov.ukBorough boundary filesGLA / London Datastore https://data.london.gov.uk/dataset/statistical-gis-boundary-files-londonBorough income estimatesGLA Economics https://data.london.gov.uk/dataset/household-income-estimates-small-areasLTDS travel reportTransport for London https://tfl.gov.uk/corporate/publications-and-reports/travel-in-london-reports

Rail & Disruption Data
WhatOfficial SourceURLORR data portalOffice of Rail and Road
https://dataportal.orr.gov.ukNetwork Rail open dataNetwork Railhttps://www.networkrail.co.uk/who-we-are/transparency-and-ethics/transparency/open-data-feedsDelay attribution dataORRhttps://dataportal.orr.gov.uk/statistics/performance/delay-attribution

Passenger & Impact Data
WhatOfficial SourceURLTransport Focus surveysTransport Focushttps://www.transportfocus.org.uk/research-publicationsLondon TravelWatch reportsLondon TravelWatchhttps://www.londontravelwatch.org.uk/resources/publicationsTrust for London dataTrust for Londonhttps://trustforlondon.org.uk/dataNomis labour market dataONS Nomishttps://www.nomisweb.co.uk

Strike History
WhatOfficial SourceURLLondon Underground strike historyWikipedia
https://en.wikipedia.org/wiki/London_Underground_strikesRMT union announcementsRMThttps://www.rmt.org.uk/news

## Setup and Implementation

1. Install dependencies:
   ```bash
   pip install pandas scipy streamlit plotly
   ```

2. Run data integration:
   ```bash
   python scripts/data_integration.py
   ```

3. Run correlation analysis:
   ```bash
   python scripts/correlation_analysis.py
   ```

4. Launch dashboard:
   ```bash
   streamlit run dashboard.py
   ```

## Files

- `scripts/app.py`: JSON to CSV converter
- `scripts/data_integration.py`: Merge transport and economic data
- `scripts/correlation_analysis.py`: Statistical analysis
- `dashboard.py`: Streamlit dashboard
- `data/`: Data files

## Current Status

- ✅ Data pipeline for TfL API to CSV
- ✅ Economic data integration using sample borough data
- ✅ Correlation analysis with borough-level metrics
- ✅ Streamlit dashboard with filter and correlation views
- 🔄 Next: Acquire real economic data, geospatial mapping, time-series analysis

## Sample Economic Data

Economic_data has been taken from below path and edit it accordingly :
- https://data.london.gov.uk/dataset/low-carbon-environmental-goods-and-services-sector-lcegs-snapsho-2rjz1
Sample files are available at `data/economic_data.csv` and `data/economic_data.json`.

You can provide economic data in either format:

- `data/economic_data.csv`
- `data/economic_data.json`

The integration script will automatically load JSON if CSV is not present. Use either file type for real borough-level income and employment data from GLA or ONS.

transport data has line-level disruptions, but economic data is borough-level. This links them (e.g., "Northern" line affects Camden borough). You can expand this mapping for more lines or modes (e.g., Overground, DLR).