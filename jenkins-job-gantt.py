# Description: Creates a Gantt chart of various Jenkins jobs that form a pipeline
# Requirements: Python 2.7+, Plotly (pip install plotly)
# Usage: python jenkins-job-gantt.py

# import plotly.plotly as py # use to automatically upload to cloud plotly. Must disable offline
from plotly.offline import plot  # use for offline plots. Must disable cloud upload
import plotly.figure_factory as ff
import plotly.graph_objs as go
import urllib2
import ssl
import datetime
import os
import logging
from plotly import tools


class JenkinsJobGantt(object):
    def __init__(self):
        logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', datefmt='%H:%M:%S', level=logging.INFO)

    def main(self):
        """
        Script that will generate gantt plot of jenkins jobs
        """
        logging.info("Started job")

        # Parallel jobs that start at the same time should be in the same job group
        input_data = {
            "job_groups":
                [
                    [
                        [
                            "job url 1",
                            "job url 2",
                            "job url 3",
                            "job url 4"
                        ]
                    ]
                    ,
                    [
                        [
                            "job url 5",
                            "job url 6"
                        ],
                        [
                            "job url 7",
                            "job url 8"
                        ]
                    ],
                    [
                    	[
                    		"job url 9"
                    	]
                    ]
                ]
        }

        query_job_date_1 = datetime.date(2017, 01, 04)
        query_job_date_2 = datetime.date(2017, 12, 04)

        plot_data = []

        create_plot_data(plot_data, query_job_date_1, input_data)
        create_plot_data(plot_data, query_job_date_2, input_data)

        # Create gantt chart
        fig = ff.create_gantt(plot_data,
                              title='Build pipeline timings on {} and {}'.format(query_job_date_1.isoformat(),
                                                                                 query_job_date_2.isoformat()),
                              showgrid_x=True,
                              index_col='JobName',
                              width=1200
                              )
        fig['layout']['margin'] = go.Margin(l=310, r=10)
        fig['layout']['hovermode'] = 'y'

        # Set hover-over text to duration
        for idx, val in enumerate(plot_data):
            fig['data'][idx].update(text='{} mins'.format(val['Duration']), hoverinfo='text')

        plot(fig, filename='gantt-simple-gantt-chart-{}-to-{}'.format(query_job_date_1.isoformat(),
                                                                      query_job_date_2.isoformat()))

        logging.info("Completed job")


def create_plot_data(plot_data, query_job_date, input_data):
    group_base_time = datetime.datetime(1970, 1, 1, 0, 0, 0)
    max_group_end_time = datetime.datetime(1970, 1, 1, 0, 0, 0)

    for job_groups_inner in input_data['job_groups']:
        for job_urls in job_groups_inner:
            returned_end_time = add_jobs(job_urls, group_base_time, plot_data, query_job_date)
            if returned_end_time > max_group_end_time:
                max_group_end_time = returned_end_time
        group_base_time = max_group_end_time

    logging.info("Data: {}".format(plot_data))


def add_job(url, basetime, plot_data, query_job_date):
    # Disable ssl checks since Jenkins certs aren't properly setup
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # Use proxy to get to Jenkins
    os.environ["HTTPS_PROXY"] = 'http://10.224.23.8:3128'

    response_job = urllib2.urlopen(url + "api/python", context=ctx)
    data_job = eval(response_job.read())

    job_display_name = data_job['displayName']
    logging.info("Job:  {}".format(job_display_name))

    for build in data_job['builds']:
        job_to_check_url = build['url']
        response_build = urllib2.urlopen(job_to_check_url + "api/python", context=ctx)
        data_build = eval(response_build.read())
        build_date = datetime.datetime.fromtimestamp(data_build['timestamp'] / 1e3)
        if data_build['result'] == 'SUCCESS':
            successful_build_duration = data_build['duration'] / 1000 / 60
            if build_date.date() <= query_job_date:
                successful_build_duration = data_build['duration'] / 1000 / 60
                logging.info("Specific job found: Date: {}, Duration: {}, Job url: {}".format(build_date,
                                                                                              successful_build_duration,
                                                                                              data_build['url']))
                break

    if not 'successful_build_duration' in locals():
        logging.error('No successful build found, using duration of 0')
        successful_build_duration = 0

    # Start and end time based on bast time passed in
    logging.info("Start time: {:%Y-%m-%d %H:%M:%S}".format(basetime))
    end_date = basetime + datetime.timedelta(minutes=successful_build_duration)
    logging.info("End time: {:%Y-%m-%d %H:%M:%S}".format(end_date))
    logging.info("---------------------------------")

    # Add to master dataset to plot. Task, Start and Finish are mandatory
    task_display_name = job_display_name.replace('[POC]', '') \
                            .replace('[A]', '') \
                            .replace('[B]', '') \
                            .replace('[ATCM]', '') \
                        + query_job_date.strftime(' %d-%m-%y')
    plot_data.append(dict(Task=task_display_name, Start=basetime, Finish=end_date, JobName=job_display_name,
                          Duration=successful_build_duration))

    return end_date


def add_jobs(job_urls, time, plot_data, query_job_date):
    for url in job_urls:
        time = add_job(url, time, plot_data, query_job_date)
    return time


if __name__ == '__main__':
    JenkinsJobGantt().main()
