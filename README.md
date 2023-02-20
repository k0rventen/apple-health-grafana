# Apple Health Grafana

Tool to import your Apple Health Data in Influx and visualize them in Grafana.

![metrics](example1.png)
![routes](example2.png)

## Export your Apple health Data

From [support.apple.com](https://support.apple.com/guide/iphone/share-your-health-data-iph5ede58c3d/ios):
```
Share your health and fitness data in XML format

You can export all of your health and fitness data from Health in XML format, which is a common format for sharing data between apps.

    Tap your profile picture or initials at the top right.

    If you don’t see your profile picture or initials, tap Summary or Browse at the bottom of the screen, then scroll to the top of the screen.

    Tap Export all health data, then choose a method for sharing your data.
```

This will create a .zip file that can be shared from the iPhone via Airdrop, messages, mail and so on.

Once you've copied/shared the file to your computer, note the path of the file (can be something like /home/me/downloads/export.zip)

## Launching the stack

You'll need docker and docker-compose installed.

Clone the repo:

```sh
git clone https://github.com/k0rventen/apple-health-grafana.git
```

Change the following line in the `docker-compose.yml`:

```yaml
    volumes:
    - <local_path_to_export.zip>:/export.zip
```

by replacing the `<local_path_to_export.zip>` with your actual health data export file path from the previous step, eg __/home/me/downloads/export.zip__:

```yaml
    volumes:
    - /home/me/downloads/export.zip:/export.zip
```

Then simply run `docker-compose up`. You should see some logs from influx & grafana, then some from the ingester container.
Wait for a log saying that all the data have been imported.

_Note: Depending on the amount of data the export has, it can take a few minutes to work through, and it may use a significant amount of resources. As an example, loading nearly 3 years of data (2 millions data points) on a Raspberry Pi 4 took around 6 minutes and used a maximum of 2.8Gig of memory._


## Visualization and next steps


Head to __http://localhost:3000__, and log with the grafana creds from the compose file (defaults to `admin`:`health`).

You should see some graphs with metrics in them.
3 dashboards are created by default:
- a generic one displaying every metric available, 
- a more refined one for specific metrics that are probably present , like walking distance, hearth related metrics..
- a workout routes one, that shows a GPS map of your outdoor routes (walking/running/biking).


## Tips on analyzing the data

Some metrics can be displayed __as is__, but others might need tweaking in the influx request:
- adjusting the time interval to 1d.
- using __sum()__ instead of __mean()__ to aggregate the metrics for a given interval
