import base64
import os
import gitlab
import requests
import json
import urllib3
import re
import xml.etree.ElementTree as ET
from jenkins import Jenkins
from st2client.client import Client
from requests.auth import HTTPBasicAuth
from base import BaseJiraAction
from common_lib import *


class JenkinscdProdExecutePermissionAction(BaseJiraAction):
    def run(self,issue_key):
        os.environ['PYTHONHTTPSVERIFY'] = "0"
        urllib3.disable_warnings()
        jenkins_username = self.config["jenkins_user"]
        jenkins_url = self.config["jenkins_url"]
        git_url = self.config['git_domain']
        issue = self._client.issue(issue_key)
        base_function.add_working_label(issue)
        base_handler = base_function(self.config)
        try:
            whos = issue.raw['fields']["customfield_11849"]
            job_or_view = issue.raw['fields']['customfield_12034']['value']
            views = issue.raw['fields']["customfield_12035"]

            # Get token
            client = Client(base_url='http://localhost')
            jenkins_password = client.keys.get_by_name(name='jenkins_secret', decrypt=True).value
            git_password = client.keys.get_by_name(name='git_api_token', decrypt=True).value

            self.result_dict = {}
            self.output_list = []
            self.result_dict['Illegal Jenkins User ID was removed'] = []

            # check view_or_job_action
            if job_or_view is None:
                raise Exception("view_or_job_action can't be None")
            elif job_or_view == 'view':
                for view in views:
                    jobs = self.getJobNameOfOneView(view,jenkins_url,jenkins_username,jenkins_password)
            else :
                jobs = views

            # check Jenkins User IDs
            if whos is None:
                raise Exception("Jenkins User IDs can't be None")
            illegal_user,whos = self.check_user_exist(jenkins_url,whos)
            if illegal_user != []:
                self.result_dict['Illegal Jenkins User ID was removed'] = " Cannot find jenkins user which named %s in current jenkins, " \
                  "please login jenkins with your pingfed first or check whether " \
                  "your ID is correct or not!!!" % (illegal_user,)
            if whos == []:
                raise Exception("Hasn't Available Jenkins User IDs")

            # elif not self.check_user_exist(jenkins_url):
            #     raise Exception("Cannot find jenkins user in current jenkins")

            # add user to job
            for job in jobs:
                    if job != "cd-yennefer-goldradar-fe" and job != "cd_data_platform_ansible_cd_kyligence" and job != "cd_paas_file_service":
                        gitUrl,gitlabProject,scriptPath = self.getConfig(job,jenkins_username,jenkins_password)
                        self.ChangGitlabFile(git_url,gitlabProject, gitUrl, scriptPath, issue_key,git_password,job)
                    else:
                        self.result_dict["illegal job's name"] = "job's name can't be cd-yennefer-goldradar-fe,cd_data_platform_ansible_cd_kyligence and cd_paas_file_service"

        except Exception as e:
            print(e)
            return False, repr(e)

        if len(self.result_dict) > 0:
            self.output_list.append("Fail info:")
            for username in self.result_dict:
                self.output_list.append("{color:#de350b}%s{color}:%s" % (username, self.result_dict[username]))
        return True, "\n".join(self.output_list)



    def getJobNameOfOneView(self,jenkins_url,view,jenkins_username,jenkins_password):
        data = []
        viewUrl = jenkins_url+'/view/' + view + '/api/json?tree=jobs[name]'
        # res = requests.get(viewUrl, auth=HTTPBasicAuth('gong.rg', "5a85a8147b0d442bf27b4961a7442fee"), verify=False)
        res = requests.get(viewUrl, auth=HTTPBasicAuth(jenkins_username, jenkins_password), verify=False)
        jobs = json.loads(res.text)['jobs']
        for job in jobs:
            # if re.match(r'^(?!ci)(\w+)',one_job['name']):
            if re.match(r'^(?!ci)(\w+)',job['name']):
                if re.match(r'(?!yjj-test)',job['name']):
                    data.append(job['name'])
        return data


    def check_user_exist(self,jenkins_url,whos):
        illegal_list = []
        for who in whos:
            url = jenkins_url+'/user/' + who
            req = requests.get(url, verify=False, timeout=3600)
            if req.status_code != 200:
                illegal_list.append(who)
                whos.remove(who)
        return illegal_list , whos


    def getConfig(self,job,jenkins_username,jenkins_password):
        # server = Jenkins("https://jenkins.cn-x-cloud-pg.com.cn",username="gong.rg",password="5a85a8147b0d442bf27b4961a7442fee",timeout=3600)

        server = Jenkins("https://jenkins.cn-x-cloud-pg.com.cn",username=jenkins_username,password=jenkins_password,timeout=3600)
        jobConfig = server.get_job_config(job)
        root = ET.fromstring(jobConfig)
        for i in root.iter('url'):
            gitlabProject = i.text.split('/')[-1].split('.')[0]
        for j in root.iter('scriptPath'):
            scriptPath = j.text
        return (i.text,gitlabProject,scriptPath)



    def ChangGitlabFile(self,git_url,gitlabProject,gitUrl,scriptPath,ticketID,git_password,job,whos):
        # gl = gitlab.Gitlab('https://gitlab.cn-x-cloud-pg.com.cn', ssl_verify=False, private_token='NwBuTvDFc9qnj6pj4aFq')
        gl = gitlab.Gitlab(git_url, ssl_verify=False, private_token=git_password)
        projects = gl.projects.list(search=(gitlabProject))
        for project in projects:
            if project.attributes['ssh_url_to_repo'] == gitUrl:
                try:
                    project.branches.get(ticketID)
                except:
                    project.branches.create({'branch': ticketID, 'ref': 'master'})
                f = project.files.get(file_path=scriptPath, ref=ticketID)
                # print(f.decode().decode())
                exec_whos = ''
                for who in whos:
                    if who not in f.decode().decode():
                        if 'project_leaders' in f.decode().decode():
                            text1 = re.findall('.*project_leaders\s*=\s*\'(.*)\'',f.decode().decode())[0]
                            # text2 = text1 + ',' + who
                            # newContent = f.decode().decode().replace(text1,text2)
                            exec_whos = exec_whos + ',' + who
                        if 'deploy_prod_leaders' in f.decode().decode():
                            text1 = re.findall('.*deploy_prod_leaders\s*=\s*\'(.*)\'', f.decode().decode())[0]
                            exec_whos = exec_whos + ',' + who
                if exec_whos:
                    text2 = text1 + exec_whos
                    newContent = f.decode().decode().replace(text1, text2)
                    f.content = base64.b64encode(newContent.encode()).decode()
                    f.save(branch=ticketID, commit_message=ticketID, encoding='base64')
                    mr = project.mergerequests.create({'source_branch': ticketID,
                                                       'target_branch': 'master',
                                                       'title': ticketID,
                                                       'description': ticketID})
                    mr.save()
                    mr.merge()
                    self.output_list.append("%s was successfully added to %s" % (exec_whos.lstrip(","),job))
                else:
                    self.result_dict['add user failed'] = "%s already exists in %s" % (whos,job)



