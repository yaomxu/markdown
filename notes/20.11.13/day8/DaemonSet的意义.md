DaemonSet 的主要作用，是让你在 Kubernetes 集群里，运行一个 Daemon Pod。

这个 Pod 三个特征：

1、这个 Pod 运行在 Kubernetes 集群里的每一个节点（Node）上；

2、每个节点上只有一个这样的 Pod 实例；

3、当有新的节点加入 Kubernetes 集群后，该 Pod 会自动地在新节点上被创建出来；而当旧节点被删除后，它上面的 Pod 也相应地会被回收掉。


Daemon Pod的意义

1、各种网络插件的 Agent 组件，都必须运行在每一个节点上，用来处理这个节点上的容器网络；

2、各种存储插件的 Agent 组件，也必须运行在每一个节点上，用来在这个节点上挂载远程存储目录，操作容器的 Volume 目录；

3、各种监控组件和日志组件，也必须运行在每一个节点上，负责这个节点上的监控信息和日志搜集。


在指定的Node上创建新的Pod：DaemonSet ： nodeAffinity

    apiVersion: v1
    kind: Pod
    metadata:
      name: with-node-affinity
    spec:
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
            - matchExpressions:
              - key: metadata.name
                operator: In
                values:
                - node-geektime


1、requiredDuringSchedulingIgnoredDuringExecution：它的意思是说，这个 nodeAffinity 必须在每次调度的时候予以考虑。同时，这也意味着你可以设置在某些情况下不考虑这个 nodeAffinity；

2、这个 Pod，将来只允许运行在“metadata.name”是“node-geektime”的节点上。


DaemonSet Controller 会在创建 Pod 的时候，自动在这个 Pod 的 API 对象里，加上这样一个 nodeAffinity 定义


总结：

    相比于 Deployment，DaemonSet 只管理 Pod 对象，然后通过 nodeAffinity 和 Toleration 这两个调度器的小功能，保证了每个节点上有且只有一个 Pod。
    
    
    与此同时，DaemonSet 使用 ControllerRevision，来保存和管理自己对应的“版本”。这种“面向 API 对象”的设计思路，大大简化了控制器本身的逻辑，也正是 Kubernetes 项目“声明式 API”的优势所在。
    
    
    而且，相信聪明的你此时已经想到了，StatefulSet 也是直接控制 Pod 对象的，那么它是不是也在使用 ControllerRevision 进行版本管理呢？
    
    
    没错。在 Kubernetes 项目里，ControllerRevision 其实是一个通用的版本管理对象。这样，Kubernetes 项目就巧妙地避免了每种控制器都要维护一套冗余的代码和逻辑的问题。


















































































































