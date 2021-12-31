# powerstats
Reading Fronius Symo API and forward data to MySQL and Influxdb

## Docker
* `docker build -t powerstats .`
* `docker run -v /opt/docker/covidstats/data:/app/data -v /opt/docker/covidstats/ogdata:/app/ogdata --rm --name covidstats covidstats`
