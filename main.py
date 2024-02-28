import json
from dbdemos.conf import Conf, DemoConf
from dbdemos.installer import Installer
from dbdemos.job_bundler import JobBundler
from dbdemos.packager import Packager
import traceback

with open("./local_conf.json", "r") as r:
    c = json.loads(r.read())
with open("./dbdemos/resources/default_cluster_config.json", "r") as cc:
    default_cluster_template = cc.read()
with open("./dbdemos/resources/default_test_job_conf.json", "r") as cc:
    default_cluster_job_template = cc.read()

conf = Conf(c['username'], c['url'], c['org_id'], c['pat_token'],
            default_cluster_template, default_cluster_job_template,
            c['repo_staging_path'], c['repo_name'], c['repo_url'], c['branch'])

from dbdemos.dbsqlclone.utils import load_dashboard
import logging
logging.basicConfig()
load_dashboard.logger.setLevel(logging.DEBUG)

def bundle():
    bundler = JobBundler(conf)

    #custom installer bundle for JADE
    bundler.add_bundle("product_demos/Auto-Loader (cloudFiles)")
    bundler.add_bundle("product_demos/Delta-Lake-CDC-CDF")
    bundler.add_bundle("product_demos/Delta-Lake")
    bundler.add_bundle("product_demos/Delta-Live-Table/Delta-Live-Table-CDC")
    #bundler.add_bundle("demo-retail/lakehouse-retail-c360")
    bundler.add_bundle("product_demos/Data-Science/mlops-end2end")


    # Run the jobs (only if there is a new commit since the last time, or failure, or force execution)
    bundler.start_and_wait_bundle_jobs(force_execution = False, skip_execution=True)

    packager = Packager(conf, bundler)
    packager.package_all()

#TODO: some demos have cross data dependencies & datasets get deleted by other demos installation. Retrying usually fix it
#Need to remove the dependency and fully isolate the demos.
def bundle_with_retry(max_retry = 3):
    retry = 0
    while retry <= max_retry:
        try:
            print(f"bundle - retry {retry}")
            bundle()
            break
        except Exception as e:
            retry += 1
            traceback.print_exc()
            print(str(e))

#bundle_with_retry(3)
bundle()
