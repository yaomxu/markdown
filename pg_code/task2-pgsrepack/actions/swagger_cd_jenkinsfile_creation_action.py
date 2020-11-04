# coding=utf-8
from st2client.client import Client
from base import BaseJiraAction
from common_lib import *
from git_lib import *
import json
import requests
import base64
import sys
import re

reload(sys)

sys.setdefaultencoding('utf-8')


class JenkinsFileCreationAction(BaseJiraAction):
    def run(self, issue_key):
        issue = self._client.issue(issue_key)
        client = Client(base_url='http://localhost')
        jenkins_password = client.keys.get_by_name(name='jenkins_secret', decrypt=True)
        jenkins_username = self.config["jenkins_user"]
        jenkins_url = self.config["jenkins_url"]
        git_token = client.keys.get_by_name(name='git_api_token', decrypt=True)
        domain = self.config['git_domain']
        git_project_id = self.config['git_test_project_id']
        git_jenkins_file_project_id = self.config['git_jenkins_file_project_id']
        git_jenkins_file_project_id = 3717
        special_group_template = "special_group"

        try:
            git_handle = git_operation(domain, git_token.value)
            special_data = git_handle.get_file_content(git_project_id, "cicd_template/%s" % (special_group_template,),
                                                       "master")
            if special_data is None:
                raise Exception("Cannot get view config file")
            special_data = eval(special_data)

            # get project_leaders and check them exists
            email_address = issue.raw["fields"]["customfield_10327"]
            rbac_client = self.get_jenkins_rbac_client(jenkins_username, jenkins_password.value)
            project_leaders = self.get_project_leaders(rbac_client, jenkins_url, email_address, issue_key)


            # get file
            jenkinsfile_content = self.create_jenkins_file(project_leaders)
            group_name = issue.raw['fields']['']
            job_name = 'apim-swagger-upload'
            file_path = "%s/%s/Jenkinsfile" % (group_name, job_name)
            file = [file_path, jenkinsfile_content]

            # get jenkins role_data
            role_data = self.get_all_role_data(rbac_client, jenkins_url)
            if role_data is not None:
                role_data = eval(role_data)
            else:
                raise Exception("Cannot get role data")

            # get role_name
            if group_name in special_data["view"].keys():
                jenkins_view = special_data["view"][group_name]
            else:
                jenkins_view = group_name
            if jenkins_view in special_data["role"].keys():
                role_name = special_data["role"][jenkins_view]
            else:
                role_name = jenkins_view

            # check role_name exist
            if role_name not in role_data.keys():
                if not self.add_role(rbac_client, role_name, jenkins_url):
                    raise Exception("Add role %s error"%(role_name, ))
            for user in project_leaders.split(","):
                if not self.assign_role(rbac_client, user, role_name, jenkins_url):
                    raise Exception("Error occurs while assign role for %s to %s view"%(user, role_name))

            # commit jenkinsfile to repo
            self.commit_jenkins_file(git_handle, git_jenkins_file_project_id, file, issue_key)

        except Exception as e:
            print(e)
            return False, repr(e)
        return True, issue_key

    # def get_env_data(self, domain, git_project_id, git_token, file_path, branch):
    #     try:
    #         get_file_url = '%s/api/v4/projects/%s/repository/files/%s?private_token=%s&ref=%s' \
    #                        % (domain, git_project_id, file_path.replace('/', '%2F'), git_token, branch)
    #         get_file_res = requests.get(get_file_url, verify=False)
    #         print(get_file_res)
    #         file_info = self.analyze_unicode(get_file_res.text)
    #         file_content = base64.b64decode(file_info['content'])
    #         return file_content
    #     except Exception as e:
    #         print(e)
    #         return None
    #
    # def analyze_unicode(self, text):
    #     json_str = json.dumps(text)
    #     json_result = json.loads(json_str).encode('utf-8')
    #     json_result = json.loads(json_result)
    #     return json_result

    # def analyze_cicd_url(self, url):
    #     pattern = ":([^/]+).*/([^/]+?)\.git$"
    #     matchObj = re.search(pattern, url)
    #     if matchObj:
    #         group_name = matchObj.group(1)
    #         app_name = matchObj.group(2)
    #         return group_name, app_name
    #     else:
    #         raise Exception("Invalid git url format")

    def create_jenkins_file(self, project_leaders):
        jenkins_file_list = ["@Library('PG-Shared-Pipleline-Library') _", " ApimUploadSwagger{",
                            "  project_leaders = '%s'" % (project_leaders,)]
        jenkins_file_list.append("}")
        return "\n".join(jenkins_file_list)

    def get_project_leaders(self, rbac_client, jenkins_url, email_address, issue_key):
        emails = email_address.split("\n")
        project_leaders_list = []
        not_found_list = []
        for email in emails:
            user_name = email.split("@")[0]
            is_exist = self.check_user_exist(rbac_client, jenkins_url, user_name)
            if is_exist:
                project_leaders_list.append(user_name)
            else:
                user_name = user_name.replace(".", "_")
                is_exist = self.check_user_exist(rbac_client, jenkins_url, user_name)
                if is_exist:
                    project_leaders_list.append(user_name)
                else:
                    not_found_list.append(email)
        if len(not_found_list) > 0:
            self._client.add_comment(issue_key, "Find below email addresses which cannot find jenkins account:\n%s" % (
                "\n".join(not_found_list),))
        return ",".join(project_leaders_list)

    def check_user_exist(self, rbac_client, jenkins_url, user_name):
        user_agent = 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)'
        headers = {'User-Agent': user_agent}
        search_url = "%s/search/?q=%s" % (jenkins_url, user_name)
        res = rbac_client.get(url=search_url, headers=headers, verify=False, allow_redirects=True)
        if res.status_code == 200:
            if re.search("<div>Jenkins User ID: [^<]+?</div>", res.text):
                return True
        return False

    def commit_jenkins_file(self, git_handle, project_id, files, issue_key):
        branch_name = issue_key.split("-")[1]
        try:
            git_handle.create_git_branch(project_id, branch_name)
            for ele in files:
                git_handle.create_or_update_file(project_id, branch_name, ele[0], ele[1], issue_key)
            git_handle.create_and_approve_merge_request(project_id, issue_key, branch_name)
        except Exception as e:
            print(e)
        finally:
            git_handle.delete_git_branch(project_id, branch_name)

    def get_jenkins_rbac_client(self, jenkins_username, jenkins_password):
        s = requests.session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.116 Safari/537.36"}
        s.auth = (jenkins_username, jenkins_password)
        s.cert = None
        s.verify = False
        s.headers = headers
        print(jenkins_username, jenkins_password)

        return s

    def get_all_role_data(self, rbac_client, jenkins_url):
        url = jenkins_url + "/role-strategy/strategy/getAllRoles?type=projectRoles"
        crumb = rbac_client.get(url)
        if crumb.status_code == 200:
            return crumb.text
        else:
            print(crumb.status_code)
            print(url)
            return None

    def add_role(self, rbac_client, jenkins_view, jenkins_url):
        url = jenkins_url + "/role-strategy/strategy/addRole"
        data = dict(
            type="projectRoles",
            roleName=jenkins_view,
            permissionIds='hudson.model.Item.Build,hudson.model.Item.Cancel,hudson.model.Item.Discover,hudson.model.Item.Read,jenkins.metrics.api.Metrics.View',
            overwrite=False,)
        data['pattern'] = "(^|^c[i,d][-,_])%s.*" % (jenkins_view,)
        crumb = rbac_client.post(url, data=data)
        if crumb.status_code == 200:
            return True
        else:
            print(crumb.status_code)
            print(crumb.text)
            return False

    def assign_role(self, rbac_client, user, jenkins_view, jenkins_url):
        url = jenkins_url + "/role-strategy/strategy/assignRole"
        data = dict(
            type="projectRoles",
            roleName=jenkins_view,
            sid=user)
        crumb = rbac_client.post(url, data=data)
        if crumb.status_code == 200:
            return True
        else:
            print(crumb.status_code)
            print(crumb.text)
            return False