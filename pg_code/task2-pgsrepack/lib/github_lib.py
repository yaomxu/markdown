import base64
import json
import requests
from github import Github


class github_operation(object):
    def __init__(self, domain, token):
        g = Github(login_or_token=token, base_url="%s/api/v3" % (domain,))
        self.domain = domain
        self.token = token
        self.handler = g

    def create_git_branch(self, git_project_id, branch):
        print("create branch:" + branch)
        try:
            repo = self.handler.get_repo(git_project_id)
            source_branch = 'master'
            sb = repo.get_branch(source_branch)
            repo.create_git_ref(ref='refs/heads/' + branch, sha=sb.commit.sha)
        except Exception as e:
            print(e)
            raise Exception("Error occurs while create git branch, message:%s" % (repr(e),))

    def delete_git_branch(self, git_project_id, branch):
        print("delete branch:" + branch)
        try:
            repo = self.handler.get_repo(git_project_id)
            br = repo.get_git_ref("heads/%s" % (branch,))
            br.delete()
        except Exception as e:
            print(e)
            raise Exception("Error occurs while delete git branch, message:%s" % (repr(e),))

    def create_file(self, git_project_id, branch, file_path, file_content, commit_message):
        print("create file:" + file_path)
        try:
            repo = self.handler.get_repo(git_project_id)
            repo.create_file(file_path, commit_message, file_content, branch=branch)
        except Exception as e:
            print(e)
            raise Exception("Error occurs while create git file, file path:%s, message:%s" % (file_path, repr(e)))

    def update_file(self, git_project_id, branch, file_path, file_content, commit_message):
        print("update file:" + file_path)
        try:
            repo = self.handler.get_repo(git_project_id)
            contents = repo.get_contents(file_path, ref='refs/heads/%s' % (branch, ))
            repo.update_file(contents.path, commit_message, file_content, contents.sha, branch=branch)
        except Exception as e:
            print(e)
            raise Exception("Error occurs while update git file, file path:%s, message:%s" % (file_path, repr(e)))

    def create_and_approve_merge_request(self, git_project_id, issue_key, branch):
        print("merge branch:" + branch)
        try:
            repo = self.handler.get_repo(git_project_id)
            pr = repo.create_pull(title=issue_key, body=issue_key, head=branch, base="master")
            print(pr.number)
            status = pr.merge()
            print(status)
        except Exception as e:
            print(e)
            raise Exception("Error occurs while create git branch, message:%s" % (repr(e),))

    def get_file_content(self, git_project_id, file_path, branch):
        print("get file:" + file_path)
        try:
            repo = self.handler.get_repo(git_project_id)
            content_file = repo.get_contents(file_path, ref='refs/heads/%s' % (branch, ))
            return base64.b64decode(content_file.content)
        except Exception as e:
            print(e)
            return None

    def check_file_exist(self, git_project_id, file_path, branch):
        print("check file:" + file_path)
        try:
            repo = self.handler.get_repo(git_project_id)
            content_file = repo.get_contents(file_path, branch=branch)
            return True
        except Exception as e:
            print(e)
            return False

    def check_user_exist(self, username):
        print("check user:" + username)
        try:
            user = self.handler.get_user(username)
            return True
        except Exception as e:
            print(e)
            return False

    def add_user_to_organization(self, organzation_name, admin_user, role):
        print("assign %s role to %s in %s" % (role, admin_user, organzation_name))
        try:
            org = self.handler.get_organization(organzation_name)
            print(org)
            user = self.handler.get_user(admin_user)
            org.add_to_members(user, role)
            return True, ""
        except Exception as e:
            print(e)
            return False, repr(e)
            #raise Exception("Error occurs while add people to organization, message:%s" % (repr(e),))

    def create_organization(self, organzation_name, admin_user):
        print("create organization:" + organzation_name)
        try:
            url = "%s/api/v3/admin/organizations" %(self.domain, )

            payload = {
                "login": organzation_name,
                "admin": admin_user,
                "profile_name": organzation_name
            }
            headers = {
                'Authorization': 'token {}'.format(self.token),
                'Content-Type': 'application/json'
            }
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            if response.status_code != 201:
                print(response.status_code)
                raise Exception(response.text)
            return True, ""
        except Exception as e:
            print(e)
            return False, "Error occurs while create organization"

    def protect_branch(self, repo, branch):
        print("protect branch %s in repo %s" % (branch, repo))
        try:
            repo = self.handler.get_repo(repo)
            br = repo.get_branch(branch)
            br.edit_protection()
            return True, ""
        except Exception as e:
            print(e)
            return False, repr(e)

    def create_organization_webhook(self, organzation_name):
        config = {'content_type': 'json', 'insecure_ssl': '0',
                  'url': 'http://10.126.147.13/api/v1/webhooks/createrepo?st2-api-key=YmQ0MWI2NzEyNzA5MjFjZjA0YWRhNjAxYjdjOGE2MzVmNGZkN2EzMjU1YWZmNjdjMmFiOWNiYTdkYzkxZTY5Zg'}
        events = ['repository']
        try:
            org = self.handler.get_organization(organzation_name)
            org.create_hook(name='web', config=config, events=events, active=True)
            return True, ""
        except Exception as e:
            print(e)
            return False, repr(e)

    def get_changed_files(self, repo, pr_number, sha):
        print("get changed files for %s repo with pr number %d" % (repo, pr_number))
        try:
            repo = self.handler.get_repo(repo)
            pr = repo.get_pull(pr_number)
            files = pr.get_files()
            output_dict = {}
            for change_file in files:
                content_file = repo.get_contents(change_file.filename, ref=sha)
                output_dict[change_file.filename] = base64.b64decode(content_file.content)
            return output_dict
        except Exception as e:
            print(e)
            return None

    def check_organization_exists(self,org_name):
        try:
            self.handler.get_organization(org_name)
            return True
        except:
            return False



