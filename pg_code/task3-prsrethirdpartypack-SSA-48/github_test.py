import base64, requests, json
from github import Github
from github_lib import *


try:
    org = git_handle.handler.get_organization(org2)
    print(org)
except Exception as e:
    print(e.args[0])

git_handle.create_organization(organzation_name=org2,admin_user=user)



# def create_organization(organzation_name, admin_user):
#     print("create organization:" + organzation_name)
#     try:
#         url = "%s/api/v3/admin/organizations" % (domain,)
#
#         payload = {
#             "login": organzation_name,
#             "admin": admin_user,
#             "profile_name": organzation_name
#         }
#         headers = {
#             'Authorization': 'token {}'.format(token),
#             'Content-Type': 'application/json'
#         }
#         response = requests.post(url, headers=headers, data=json.dumps(payload))
#         if response.status_code != 201:
#             print(response.status_code)
#             raise Exception(response.text)
#         return True, ""
#     except Exception as e:
#         print(e)
#         return False, "Error occurs while create organization"


#
# user = g.get_user("zhou-bz-1")
# print(user)
# org = g.get_organization("test1")
# print(org)
# org.add_to_members(user, "admin")
# login = user.login
# repo = g.get_repo("test1/abcd")
# print(repo.name)
# print(repo.id)
# content_file = repo.get_contents("file1", ref='a8499d12d9ce10e5dc861c76f0a2d5dccc6470b3')
# print(base64.b64decode(content_file.content))
# content_file = repo.get_contents("file1", ref='f7823f4e28b32d1b3959e276526f5d1b7e4e9b71')
# print(base64.b64decode(content_file.content))
# commit = repo.get_commit("f7823f4e28b32d1b3959e276526f5d1b7e4e9b71")
# print(commit.files)
# for i in commit.files:
#     if i.filename == "file1":
#         print(i.contents_url)

# print(type(contents))
# for content_file in contents:
#     print(content_file)
#     print(base64.b64decode(content_file.content))


# source_branch = 'master'
# target_branch = 'test'
# sb = repo.get_branch(source_branch)
# repo.create_git_ref(ref='refs/heads/' + target_branch, sha=sb.commit.sha)

# repo.create_file("test.txt", "for test", "test content", branch="test")

# contents = repo.get_contents("test.txt", ref="test")
# repo.update_file(contents.path, "more tests", "more tests", contents.sha, branch="test")

# pr = repo.create_pull(title="test pr", body='test body', head="test", base="master")
# print(pr.number)
# status = pr.merge()
# print(status)

# br = repo.get_git_ref("heads/test")
# print(br)
# br.delete()

# br = repo.get_branch("master")
# print(br)
# br.edit_protection(user_push_restrictions=[])

# token = "dcecb27fd73bbe7a504d435bfcbf38de206ee227"
# url = "https://github.cn-pgcloud.com/api/v3/admin/organizations"
#
# payload = {
#     "login": "test1",
#     "admin": "paasRobotAdmin",
#     "profile_name": "auto test"
# }
# headers = {
#     'Authorization': 'token {}'.format(token),
#     'Content-Type': 'application/json'
# }
# print(headers)
# try:
#     response = requests.post(url, headers=headers, data=json.dumps(payload))
#     print(response.status_code)
#     print(response.text)
# except Exception as e:
#     print(e)
