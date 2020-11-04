import requests, json, base64
import gitlab

class git_operation(object):
    def __init__(self,domain,token):
        self.domain = domain
        self.token = token
        self.gl = gitlab.Gitlab(self.domain, ssl_verify=False, private_token=self.token)

    def check_group_exists(self,git_group):
        try:
            self.gl.groups.get(git_group)
            return True
        except:
            return False

    def create_git_branch(self, git_project_id, branch):
        print("create branch:" + branch)
        create_git_branch_url = '%s/api/v4/projects/%s/repository/branches?private_token=%s&branch=%s' \
                                '&ref=master' \
                                % (self.domain, git_project_id, self.token, branch)
        requests.post(create_git_branch_url, verify=False)

    def delete_git_branch(self, git_project_id, branch):
        print("delete branch:" + branch)
        delete_git_branch_url = '%s/api/v4/projects/%s/repository/branches/%s?private_token=%s' \
                                % (self.domain, git_project_id, branch, self.token)
        res = requests.delete(delete_git_branch_url, verify=False)
        print res.text

    def create_or_update_file(self,git_project_id, branch, file_path, file_content, commit_message):
        print("create/update file:" + file_path)
        create_file_url = '%s/api/v4/projects/%s/repository/files/%s?private_token=%s&content=%s&branch=%s' \
                          '&commit_message=%s' \
                          % (self.domain, git_project_id, file_path.replace('/', '%2F'), self.token,
                             file_content, branch, commit_message)

        update_file_res = requests.post(create_file_url, verify=False)
        if "A file with this name already exists" in update_file_res.text:
            update_file_res = requests.put(create_file_url, verify=False)
        print(update_file_res.text)

    def create_and_approve_merge_request(self, git_project_id, issue_key, branch):
        print("merge branch:" + branch)
        # create merge request
        merge_request_url = '%s/api/v4/projects/%s/merge_requests?private_token=%s&source_branch=%s&target_branch' \
                            '=master&title=%s&description=%s' \
                            % (self.domain, git_project_id, self.token, branch, issue_key, issue_key)

        merge_request_res = requests.post(merge_request_url, verify=False)
        merge_request_info = self.analyze_unicode(merge_request_res.text)

        # approve merge request
        approve_merge_request_url = '%s/api/v4/projects/%s/merge_requests/%s/merge?private_token=%s' \
                                    % (self.domain, git_project_id, merge_request_info['iid'], self.token)
        approve_merge_request_res = requests.put(approve_merge_request_url, verify=False)

    def get_file_content(self, git_project_id, file_path, branch):
        try:
            get_file_url = '%s/api/v4/projects/%s/repository/files/%s?private_token=%s&ref=%s' \
                           % (self.domain, git_project_id, file_path.replace('/', '%2F'), self.token, branch)
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

