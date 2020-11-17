# coding=utf-8
from st2client.client import Client
from base import BaseJiraAction
from common_lib import *
from jenkins_lib import *
from git_lib import *
from github_lib import *
import json
import requests
import base64
import sys
import re

reload(sys)

sys.setdefaultencoding('utf-8')


class CDCreationAction(BaseJiraAction):
    def run(self, issue_key):
        issue = self._client.issue(issue_key)
        client = Client(base_url='http://localhost')
        jenkins_password = client.keys.get_by_name(name='jenkins_secret', decrypt=True)
        jenkins_username = self.config["jenkins_user"]
        jenkins_url = self.config["jenkins_url"]
        git_token = client.keys.get_by_name(name='git_api_token', decrypt=True)
        github_token = client.keys.get_by_name(name='github_api_token', decrypt=True)
        domain = self.config['git_domain']
        github_domain = self.config['github_domain']
        git_project_id = self.config['git_test_project_id']
        job_list = []

        try:
            # check group or organization exists
            group_or_organization = issue.raw['fields']['']
            git_handle = git_operation(domain, git_token.value)
            if git_handle.check_group_exists(group_or_organization):
                template_name = "apim_swagger_template.xml"
            else :
                github_handle = github_operation(github_domain,github_token.value)
                if github_handle.check_organization_exists(group_or_organization):
                    template_name = "apim_swagger_template_github.xml"
                else:
                    raise Exception("no such group/organization")

            # get template
            if template_name:
                template = self.get_cd_template(domain, git_project_id, git_token.value,
                                                "cicd_template/%s" % (template_name,), "master")
            if template is None :
                raise Exception("Cannot get CD template")

            # check view exists
            jenkins_handle = jenkins_operation(jenkins_url, jenkins_username, jenkins_password.value)
            view_name = group_or_organization
            if not jenkins_handle.check_view_exist(view_name) :
                jenkins_handle.add_view(view_name)
                job_list.append("add view: %s"%view_name)

            # check job exists
            job_name = 'apim-swagger-upload'
            cd_job_name = "-".join([view_name, job_name]).replace("_", "-").replace("--", "-")
            all_jobs = jenkins_handle.get_all_jobs()
            job_str = ",".join(all_jobs)
            pattern = "(%s)" % (cd_job_name.replace("-", "(-|_)"),)
            matchObj = re.search(pattern, job_str)
            if matchObj:
                raise Exception("cd job exists")

            # create job
            apim_env = ""
            eureka_service_id = ""
            platform = ""
            product_name = ""
            path = "%s/%s"%(view_name,job_name)
            config_xml = self.create_backend_cd_xml(template, path, apim_env, eureka_service_id, platform, product_name)
            jenkins_handle.create_job(job_name, config_xml)
            jenkins_handle.add_job_to_view(view_name, job_name)
            job_list.append("/".join([view_name, "job", job_name]))


        except Exception as e:
            print(e)
            return False, repr(e)
        return True, ",".join(job_list)

    def get_cd_template(self, domain, git_project_id, git_token, file_path, branch):
        try:
            get_file_url = '%s/api/v4/projects/%s/repository/files/%s?private_token=%s&ref=%s' \
                           % (domain, git_project_id, file_path.replace('/', '%2F'), git_token, branch)
            get_file_res = requests.get(get_file_url, verify=False)
            print(get_file_res)
            file_info = self.analyze_unicode(get_file_res.text)
            file_content = base64.b64decode(file_info['content'])
            return file_content
        except Exception as e:
            print(e)
            return None

    def analyze_unicode(self, text):
        json_str = json.dumps(text)
        json_result = json.loads(json_str).encode('utf-8')
        json_result = json.loads(json_result)
        return json_result




    def create_backend_cd_xml(self, template,path,apim_env, eureka_service_id,platform,product_name):
        template = template.replace("APIM_ENV", apim_env).replace("EUREKA_SERVICE_ID", eureka_service_id).replace("PLATFORM", platform).replace("PRODUCT_NAME", product_name)
        template = template.replace("JENKINS_FILE","%s/Jenkinsfile"%(path)).replace("{group name or org}/{jenkins job name}/Jenkinsfile","")
        # env_str = ""
        # for i in env:
        #     env_str = env_str + "<string>%s</string>\n" % (i["value"])
        # template = template.replace("$ENV$", env_str)
        return template
