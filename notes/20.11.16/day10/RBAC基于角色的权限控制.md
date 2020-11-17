能不能自己写一个编排对象？

通过一个外部插件，在K8S中新增和操作API对象

RBAC是什么？

Kubernetes 中所有的 API 对象，都保存在 Etcd 里。可是，对这些 API 对象的操作，却一定都是通过访问 kube-apiserver 实现的。其中一个非常重要的原因，就是你需要 APIServer 来帮助你做授权工作。


而在 Kubernetes 项目中，负责完成授权（Authorization）工作的机制，就是 RBAC：基于角色的访问控制（Role-Based Access Control）


三个基本概念：（核心）

    1、Role：角色，它其实是一组规则，定义了一组对 Kubernetes API 对象的操作权限。
    2、Subject：被作用者，既可以是“人”，月可以是机器，也可以是在K8S里定义的“用户”。
    3、RoleBinding：定义了“被作用者”和“角色”的绑定关系


Role

Role本身就是一个K8S的API对象
定义如下：

    kind: Role
    apiVersion: rbac.authorization.k8s.io/v1
    metadata:
      namespace: mynamespace
      name: example-role
    rules:
    - apiGroups: [""]
      resources: ["pods"]
      verbs: ["get", "watch", "list"]
 
这个Role对象指定了它能产生作用的Namespace是:mynamespace


上面这个例子里，规则的含义就是：

    允许“被使用者”，对mynamespace下面的Pod独享，进行GET、WATCH和LIST操作
    
        “被使用者”是如何指定的？
    
            通过RoleBinding来实现


RoleBinding也是一个K8S的API对象

    kind: RoleBinding
    apiVersion: rbac.authorization.k8s.io/v1
    metadata:
      name: example-rolebinding
      namespace: mynamespace
    subjects:
    - kind: User
      name: example-user
      apiGroup: rbac.authorization.k8s.io
    roleRef:
      kind: Role
      name: example-role
      apiGroup: rbac.authorization.k8s.io
 
把“被使用者”绑定到Role （subject字段定义被使用者，roleRef字段把被使用者绑定到定义好的Role对象中）


subjects字段，定义“被使用者”。

类型是User，即K8S里的用户。

这个用户名是example-user


roleRef字段：
通过这个字段，RoleBinding 对象就可以直接通过名字，来引用我们前面定义的 Role 对象（example-role），从而定义了“被作用者（Subject）”和“角色（Role）”之间的绑定关系。


注意：Role 和 RoleBinding 对象都是 Namespaced 对象（Namespaced Object）


操作非Namespace对象，或者说某一个 Role 想要作用于所有的 Namespace 的时候，该如何去做授权？

ClusterRole 和 ClusterRoleBinding 组合

    kind: ClusterRole
    apiVersion: rbac.authorization.k8s.io/v1
    metadata:
      name: example-clusterrole
    rules:
    - apiGroups: [""]
      resources: ["pods"]
      verbs: ["get", "watch", "list"]
    kind: ClusterRoleBinding
    apiVersion: rbac.authorization.k8s.io/v1
    metadata:
      name: example-clusterrolebinding
    subjects:
    - kind: User
      name: example-user
      apiGroup: rbac.authorization.k8s.io
    roleRef:
      kind: ClusterRole
      name: example-clusterrole
      apiGroup: rbac.authorization.k8s.io
 
注意，没有了Namespace字段，这两个API对象用法和Role和RoleBinding一样


上面的例子里的 ClusterRole 和 ClusterRoleBinding 的组合，意味着名叫 example-user 的用户，拥有对所有 Namespace 里的 Pod 进行 GET、WATCH 和 LIST 操作的权限。

verbs字段的全集：
（所有权限）

    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]


类似地，Role对象的rules字段也可以细化。


（只针对某一个具体的对象进行权限设置）

    rules:
    - apiGroups: [""]
      resources: ["configmaps"]
      resourceNames: ["my-config"]
      verbs: ["get"]
     
“被使用者” 只对“my-config”这个ConfigMap对象有GET操作的权限


大多时候，“用户”这个功能用的比较少，而是直接使用K8S里的“内置用户”


这个由 Kubernetes 负责管理的“内置用户”，正是我们前面曾经提到过的：ServiceAccount。


1、首先，我们要定义一个 ServiceAccount

    apiVersion: v1
    kind: ServiceAccount
    metadata:
      namespace: mynamespace
      name: example-sa
    只需要Name和Namespace两个最基本的字段


2、编写 RoleBinding 的 YAML 文件，来为这个 ServiceAccount 分配权限：

    kind: RoleBinding
    apiVersion: rbac.authorization.k8s.io/v1
    metadata:
      name: example-rolebinding
      namespace: mynamespace
    subjects:
    - kind: ServiceAccount
      name: example-sa
      namespace: mynamespace
    roleRef:
      kind: Role
      name: example-role
      apiGroup: rbac.authorization.k8s.io


注意：这个subjects字段的kind，不再是User，而是ServiceAccount

而roleRef字段的Role对象，仍然是example-role（前面定义的Role对象）


3、创建这三个对象

    $ kubectl create -f svc-account.yaml
    $ kubectl create -f role-binding.yaml
    $ kubectl create -f role.yaml


然后，我们来查看一下这个 ServiceAccount 的详细信息：

    $ kubectl get sa -n mynamespace -o yaml
    - apiVersion: v1
      kind: ServiceAccount
      metadata:
        creationTimestamp: 2018-09-08T12:59:17Z
        name: example-sa
        namespace: mynamespace
        resourceVersion: "409327"
        ...
      secrets:
      - name: example-sa-token-vmfg6
     
Kubernetes 会为一个 ServiceAccount 自动创建并分配一个 Secret 对象，即：上述 ServiceAcount 定义里最下面的 secrets 字段。


这个 Secret，就是这个 ServiceAccount 对应的、用来跟 APIServer 进行交互的授权文件，我们一般称它为：Token。Token 文件的内容一般是证书或者密码，它以一个 Secret 对象的方式保存在 Etcd 当中。


4、定义Pod，声明使用这个ServiceAccount

比如下面这个例子：

    apiVersion: v1
    kind: Pod
    metadata:
      namespace: mynamespace
      name: sa-token-test
    spec:
      containers:
      - name: nginx
        image: nginx:1.7.9
      serviceAccountName: example-sa


等这个 Pod 运行起来之后，我们就可以看到，该 ServiceAccount 的 token，也就是一个 Secret 对象，被 Kubernetes 自动挂载到了容器的 /var/run/secrets/kubernetes.io/serviceaccount 目录下，如下所示：

（通过 kubectl decribe pod查看Containers字段的Mounts）

    $ kubectl describe pod sa-token-test -n mynamespace
    Name:               sa-token-test
    Namespace:          mynamespace
    ...
    Containers:
      nginx:
        ...
        Mounts:
          /var/run/secrets/kubernetes.io/serviceaccount from example-sa-token-vmfg6 (ro)


这时候，我们可以通过 kubectl exec 查看到这个目录里的文件：

    $ kubectl exec -it sa-token-test -n mynamespace -- /bin/bash
    root@sa-token-test:/# ls /var/run/secrets/kubernetes.io/serviceaccount
    ca.crt namespace token
    
如上所示，容器里的应用，就可以使用这个 ca.crt 来访问 APIServer 了。更重要的是，此时它只能够做 GET、WATCH 和 LIST 操作。因为 example-sa 这个 ServiceAccount 的权限，已经被我们绑定了 Role 做了限制。



除了前面使用的“用户”（User），Kubernetes 还拥有“用户组”（Group）的概念，也就是一组“用户”的意思。如果你为 Kubernetes 配置了外部认证服务的话，这个“用户组”的概念就会由外部认证服务提供。


而对于 Kubernetes 的内置“用户”ServiceAccount 来说，上述“用户组”的概念也同样适用。


这两个对应关系很重要：

    在K8S中 “用户”的名字是：
    system:serviceaccount:<Namespace名字>:<ServiceAccount名字>
    
    
    对应的“用户组”的名字是：
    system:serviceaccounts:<Namespace名字>




1、比如，现在我们可以在 RoleBinding 里定义如下的 subjects：

    subjects:
    - kind: Group
      name: system:serviceaccounts:mynamespace
      apiGroup: rbac.authorization.k8s.io
     
name定义的是 一个“用户组”

这就意味着这个 Role 的权限规则，作用于 mynamespace 里的所有 ServiceAccount。这就用到了“用户组”的概念。


2、下面这个例子：

    subjects:
    - kind: Group
      name: system:serviceaccounts
      apiGroup: rbac.authorization.k8s.io
     
name定义的是所有的“用户组”

就意味着这个 Role 的权限规则，作用于整个系统里的所有 ServiceAccount。



总结：
Role：一组权限规则列表
RoleBinding：


