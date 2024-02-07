from dbdemos.conf import DemoConf

from .tracker import Tracker
import urllib
import re
import base64
import json

class NotebookParser:

    def __init__(self, html):
        self.html = html
        self.raw_content, self.content = self.get_notebook_content(html)

    def get_notebook_content(self, html):
        match = re.search(r'__DATABRICKS_NOTEBOOK_MODEL = \'(.*?)\'', html)
        raw_content = match.group(1)
        content = base64.b64decode(raw_content).decode('utf-8')
        content = urllib.parse.unquote(content)
        return raw_content, content

    def get_html(self):
        content = urllib.parse.quote(self.content, safe="()*''")
        return self.html.replace(self.raw_content, base64.b64encode(content.encode('utf-8')).decode('utf-8'))

    def contains(self, str):
        return str in self.content

    def remove_static_settings(self):
        #Remove the static settings tags are it's too big & unecessary to repeat in each notebook.
        self.html = re.sub("""<script>\s?window\.__STATIC_SETTINGS__.*</script>""", "", self.html)

    def set_tracker_tag(self, org_id, uid, category, demo_name, notebook):
        #Replace internal tags with dbdemos
        if Tracker.enable_tracker:
            tracker = Tracker(org_id, uid)
            #Our demos in the repo already have tags used when we clone the notebook directly.
            #We need to update the tracker with the demo configuration & dbdemos setup.
            tracker_url = tracker.get_track_url(category, demo_name, "VIEW", notebook)
            r = r"""(<img\s*width=\\?"1px\\?"\s*src=\\?")(https:\/\/ppxrzfxige\.execute-api\.us-west-2\.amazonaws\.com\/v1\/analytics.*?)(\\?"\s?\/?>)"""
            self.content = re.sub(r, rf'\1{tracker_url}\3', self.content)

            #old legacy tracker, to be migrted & emoved
            r = r"""(<img\s*width=\\?"1px\\?"\s*src=\\?")(https:\/\/www\.google-analytics\.com\/collect.*?)(\\?"\s?\/?>)"""
            self.content = re.sub(r, rf'\1{tracker_url}\3', self.content)
        else:
            #Remove all the tracker from the notebook
            self.replace_in_notebook(r"""<img\s*width=\\?"1px\\?"\s*src=\\?"https:\/\/www\.google-analytics\.com\/collect.*?\\?"\s?\/?>""", "", True)
            self.replace_in_notebook(r"""<img\s*width=\\?"1px\\?"\s*src=\\?"https:\/\/ppxrzfxige\.execute-api\.us-west-2\.amazonaws\.com\/v1\/analytics.*?\\?"\s?\/?>""", "", True)

    def remove_uncomment_tag(self):
        self.replace_in_notebook('[#-]{1,2}\s*UNCOMMENT_FOR_DEMO ?', '', True)

    ##Remove the __build to avoid catalog conflict during build vs test
    # TODO: improve build and get a separate metastore for tests vs build.
    def remove_dbdemos_build(self):
        self.replace_in_notebook('dbdemos__build', 'dbdemos')

    def remove_robots_meta(self):
        #Drop the noindex tag
        self.html = self.html.replace('<meta name="robots" content="nofollow, noindex">', '')

    def add_cell_as_html_for_seo(self):
        #Add div as hidden HTML for SEO to capture the main information in the page.
        def md_to_html(text):
            if text.startswith('%md-sandbox'):
                text = text[len('%md-sandbox'):]
            if text.startswith('%md'):
                text = text[len('%md'):]
            #quick translation to html for seo
            for i in reversed(range(1,6)):
                tag = "#"*i
                text = re.sub(rf'\s*{tag}\s*(.*)', rf'<h{i}>\1</h{i}>', text)
            text = text.replace('\n', '<br/>')
            return text
        #Drop the noindex tag
        content = json.loads(self.content)
        html = ""
        for c in content["commands"]:
            if c['command'].startswith('%md'):
                html += '<div>'+md_to_html(c['command'])+'</div>'
        if len(html) > 0:
            self.html = self.html.replace('<body>', f'''<body><div id='no_js_render' style='display: none'>{html}</div>''')
            self.html = self.html.replace('<script>', "<script>window.addEventListener('load', function(event) { "
                                                        "if (/bot|google|baidu|bing|msn|teoma|slurp|yandex/i.test(navigator.userAgent)) {"
                                                            "document.getElementById('no_js_render').style.display = 'block';"
                                                        "};"
                                                      "});", 1)

    def replace_schema(self, demo_conf: DemoConf):
        self.replace_in_notebook(f'catalog = \\"main__build\\"', f'catalog = \\"main\\"')
        if demo_conf.custom_schema_supported:
            self.replace_in_notebook('''\$catalog="[0-9a-z_]*"\s{1,3}\$schema="[0-9a-z_]*"''', f"$catalog={demo_conf.catalog} $schema={demo_conf.schema}", True)
            self.replace_in_notebook(f'''$catalog=\\"{demo_conf.default_catalog}\\"''', f'''$catalog=\\"{demo_conf.catalog}\\"''', False)
            self.replace_in_notebook(f'''$schema=\\"{demo_conf.default_schema}\\"''', f'''$schema=\\"{demo_conf.schema}\\"''', False)
            self.replace_in_notebook("\$catalog=[0-9a-z_]*\s{1,3}\$db=[0-9a-z_]*", f"$catalog={demo_conf.catalog} $db={demo_conf.schema}", True)
            self.replace_in_notebook(f"{demo_conf.default_catalog}.{demo_conf.default_schema}", f"{demo_conf.catalog}.{demo_conf.schema}")
            self.replace_in_notebook(f'dbutils.widgets.text(\\"catalog\\", \\"{demo_conf.default_catalog}\\"', f'dbutils.widgets.text(\\"catalog\\", \\"{demo_conf.catalog}\\"')
            self.replace_in_notebook(f'dbutils.widgets.text(\\"schema\\", \\"{demo_conf.default_schema}\\"', f'dbutils.widgets.text(\\"schema\\", \\"{demo_conf.schema}\\"')
            self.replace_in_notebook(f'dbutils.widgets.text(\\"db\\", \\"{demo_conf.default_schema}\\"', f'dbutils.widgets.text(\\"db\\", \\"{demo_conf.schema}\\"')

            self.replace_in_notebook(f'catalog = \\"{demo_conf.default_catalog}\\"', f'catalog = \\"{demo_conf.catalog}\\"')
            self.replace_in_notebook(f'dbName = db = \\"{demo_conf.default_schema}\\"', f'dbName = db = \\"{demo_conf.schema}\\"')
            self.replace_in_notebook(f'db = \\"{demo_conf.default_schema}\\"', f'db = \\"{demo_conf.schema}\\"')
            self.replace_in_notebook(f'schema = \\"{demo_conf.default_schema}\\"', f'schema = \\"{demo_conf.schema}\\"')

    def replace_in_notebook(self, old, new, regex = False):
        if regex:
            self.content = re.sub(old, new, self.content)
        else:
            self.content = self.content.replace(old, new)

    def get_dashboard_ids(self):
        pattern = re.compile(r'\/sql\/dashboards\/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', re.IGNORECASE)
        return pattern.findall(self.content)

    def add_extra_cell(self, cell_content, position = 1):
        command = {
            "version": "CommandV1",
            "bindings": {},
            "subtype": "command",
            "commandType": "auto",
            "position": position,
            "command": cell_content
        }
        content = json.loads(self.content)
        content["commands"].insert(position, command)
        self.content = json.dumps(content)

    #as auto ml links are unique per workspace, we have to delete them
    def remove_automl_result_links(self):
        content = json.loads(self.content)
        for c in content["commands"]:
            if re.search('display_automl_[a-zA-Z]*_link', c["command"]):
                if 'results' in c and c['results'] is not None and 'data' in c['results'] and c['results']['data'] is not None and len(c['results']['data']) > 0:
                    contains_exp_link = len([d for d in c['results']['data'] if 'Data exploration notebook' in d['data']]) > 0
                    if contains_exp_link:
                        c['results']['data'] = [{'type': 'ansi', 'data': 'Please run the notebook cells to get your AutoML links (from the begining)', 'name': None, 'arguments': {}, 'addedWidgets': {}, 'removedWidgets': [], 'datasetInfos': [], 'metadata': {}}]
        self.content = json.dumps(content)


    #Will change the content to
    def change_relative_links_for_minisite(self):
        #self.replace_in_notebook("""<a\s*(?:target="_blank")?\s*(?:rel="noopener noreferrer")?\s*href="\$\.\/(.*)">""", """<a href="./$1">""", True)
        self.replace_in_notebook("""\]\(\$\.\/(.*?)\)""", """](./\g<1>.html)""", True)


    def add_javascript_to_minisite_relative_links(self):
        self.html = re.sub("""</body>""",
            """<script type="text/javascript">
                function removeDollarFromLinks() {
                  const links = document.getElementsByTagName("a");
            
                  for (let i = 0; i < links.length; i++) {
                    const href = links[i].getAttribute("href");
            
                    if (href && href.includes("$")) {
                      const newHref = href.replace(/\$/g, "");
                      links[i].setAttribute("href", newHref+".html");
            
                      if (links[i].hasAttribute("target")) {
                        links[i].removeAttribute("target");
                      }
                    }
                  }
                }
                window.addEventListener('load', function(event) {
                    removeDollarFromLinks()
                });
            </script>
            </body>""", self.html)

    def add_ga_website_tracker(self):
        if False: #Tracker.enable_tracker:
            tracker = """
            <head>
            <!-- Cookie Consent by TermsFeed https://www.TermsFeed.com -->
            <script type="text/javascript" src="https://www.termsfeed.com/public/cookie-consent/4.1.0/cookie-consent.js" charset="UTF-8"></script>
            <script type="text/javascript" charset="UTF-8">
            document.addEventListener('DOMContentLoaded', function () {
                        cookieconsent.run({"notice_banner_type":"simple","consent_type":"express","palette":"light","language":"en","page_load_consent_levels":["strictly-necessary"],"notice_banner_reject_button_hide":false,"preferences_center_close_button_hide":false,"page_refresh_confirmation_buttons":false,"website_name":"dbdemos.ai","website_privacy_policy_url":"https://dbdemos.ai/privacy-policy"});
                        });
            </script>
            <!-- analytics -->
            <script type="text/plain" data-cookie-consent="tracking" async src="https://www.googletagmanager.com/gtag/js?id="""+Tracker.website_tracker_id+""""></script>
            <script type="text/plain" data-cookie-consent="tracking">
              window.dataLayer = window.dataLayer || [];
              function gtag(){dataLayer.push(arguments);}
              gtag('js', new Date());
            
              gtag('config', '"""+Tracker.website_tracker_id+"""');
            </script>
            <!-- end of analytics-->
            <a href="#" id="open_preferences_center">Update cookies preferences</a>
            """
            self.html = re.sub("""<head>""", tracker, self.html)

    def hide_commands_and_results(self):
        #
        self.replace_in_notebook('e2-demo-tools', 'xxxx', True)
        content = json.loads(self.content)
        for c in content["commands"]:
            if "#hide_this_code" in c["command"].lower():
                c["hideCommandCode"] = True
            if "%run " in c["command"]:
                c["hideCommandResult"] = True
            if "results" in c and  c["results"] is not None and "data" in c["results"] and c["results"]["data"] is not None and \
                    c["results"]["type"] == "table" and len(c["results"]["data"])>0 and str(c["results"]["data"][0][0]).startswith("This Delta Live Tables query is syntactically valid"):
                c["hideCommandResult"] = True
        self.content = json.dumps(content)

    def remove_delete_cell(self):
        content = json.loads(self.content)
        content["commands"] = [c for c in content["commands"] if "#dbdemos__delete_this_cell" not in c["command"].lower()]
        self.content = json.dumps(content)

    def replace_dashboard_links(self, dashboards):
        def replace_link_with_error(pattern, c):
            for p in pattern.findall(c["command"]):
                c["command"] = c["command"].replace(p[0], f"{p[1]}: ERROR - could not load the dashboard {d['name']}. {d['error']}")
        if "sql/dashboards" in self.content:
            content = json.loads(self.content)
            for d in dashboards:
                pattern1 = re.compile(rf'\[(.*?)\]\(\/sql\/dashboards\/{d["id"]}.*?\)', re.IGNORECASE)
                pattern2 = re.compile(rf'(<a.*?\/sql\/dashboards\/{d["id"]}.*?>(.*?)</a>)', re.IGNORECASE)
                for c in content["commands"]:
                    if "sql/dashboards" in c["command"]:
                        if d["installed_id"] is None:
                            replace_link_with_error(pattern1, c)
                            replace_link_with_error(pattern2, c)
                        else:
                            c["command"] = c["command"].replace(d['id'], d["installed_id"])
            self.content = json.dumps(content)

    def replace_dynamic_links(self, items, name, link_path):
        matches = re.finditer(rf'<a\s*dbdemos-{name}-id=\\?"(?P<item_id>.*?)\\?"\s*href=\\?".*?\/?{link_path}\/(?P<item_uid>[a-zA-Z0-9_-]*).*?>', self.content)
        for match in matches:
            item_id = match.groupdict()["item_id"]
            installed = False
            for i in items:
                if i["id"] == item_id:
                    installed = True
                    self.content = self.content.replace(match.groupdict()["item_uid"], str(i['uid']))
            if not installed:
                print(f'''ERROR: couldn't find {name} with dbdemos-{name}-id={item_id}''')


    def replace_dynamic_links_workflow(self, workflows):
        """
        Replace the links in the notebook with the workflow installed if any
        """
        self.replace_dynamic_links(workflows, "workflow", "#job")

    def replace_dynamic_links_repo(self, repos):
        for r in repos:
            if r["uid"].startswith("/"):
                r["uid"] = r["uid"][1:]
        """
        Replace the links in the notebook with the repos installed if any
        """
        self.replace_dynamic_links(repos, "repo", "#workspace")

    def replace_dynamic_links_pipeline(self, pipelines_id):
        """
        Replace the links in the notebook with the DLT pipeline installed if any
        """
        self.replace_dynamic_links(pipelines_id, "pipeline", "#joblist/pipelines")