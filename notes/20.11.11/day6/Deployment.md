Deployment--> 控制 --> ReplicaSet对象 --> 控制 --> Pod

创建一个Deployment后，会创建一个 ReplicaSet对象，进而创建 Pod

Deployment 实现了 Kubernetes 项目中一个非常重要的功能：Pod 的“水平扩展 / 收缩”（horizontal scaling out/in）

假如 更新的Deployment的Pod模板（比如，修改了容器的镜像），那么Deployment就需要遵循一种叫做 “ 滚动更新 ”（roolling update）的方式，来升级现有的容器

这个能力依赖的是Kubernetes 项目中的一个非常重要的概念（API 对象）：ReplicaSet 

ReplicaSet结构 yaml文件
    
    apiVersion: apps/v1
    kind: ReplicaSet
    metadata:
      name: nginx-set
      labels:
        app: nginx
    spec:
      replicas: 3
      selector:
        matchLabels:
          app: nginx
      template:
        metadata:
          labels:
            app: nginx
        spec:
          containers:
          - name: nginx
            image: nginx:1.7.9

我们可以看到，一个 ReplicaSet 对象，其实就是由副本数目的定义和一个 Pod 模板组成的。不难发现，它的定义其实是 Deployment 的一个子集。
Deployment 控制器实际操纵的，正是这样的 ReplicaSet 对象，而不是 Pod 对象。

对于一个 Deployment 所管理的 Pod，它的 ownerReference 是谁？
    ReplicaSet
如下： 

    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: nginx-deployment
      labels:
        app: nginx
    spec:
      replicas: 3
      selector:
        matchLabels:
          app: nginx
      template:
        metadata:
          labels:
            app: nginx
        spec:
          containers:
          - name: nginx
            image: nginx:1.7.9
            ports:
            - containerPort: 80       
               
    #这是一个nginx-deployment，它定义的 Pod 副本个数是 3（spec.replicas=3）  
            
Deployment 控制 ReplicaSet 控制 Pod 
一个定义了 replicas=3 的 Deployment，与它的 ReplicaSet，以及 Pod 的关系，实际上是一种“层层控制”的关系
ReplicaSet 负责通过“控制器模式”，保证系统中 Pod 的个数永远等于指定的个数（比如，3 个）。这也正是 Deployment 只允许容器的 restartPolicy=Always 的主要原因：只有在容器能保证自己始终是 Running 状态的前提下，ReplicaSet 调整 Pod 的个数才有意义。
而在此基础上，Deployment 同样通过“控制器模式”，来操作 ReplicaSet 的个数和属性，进而实现“水平扩展 / 收缩”和“滚动更新”这两个编排动作。

水平扩展 / 收缩：
改replicas的值：
kubectl scale
如            
    $ kubectl scale deployment nginx-deployment --replicas=4
    deployment.apps/nginx-deployment scaled
                

滚动更新”是什么意思，如何实现的？

    1、创建这个 nginx-deployment：
        $ kubectl create -f nginx-deployment.yaml --record
        （–record 参数。它的作用，是记录下你每次操作所执行的命令，以方便后面查看。）
    
    2、检查一下nginx-deployment 创建后的状态信息：
        $ kubectl get deployments
        NAME               DESIRED   CURRENT   UP-TO-DATE   AVAILABLE   AGE
        nginx-deployment   3         0         0            0           1s

        DESIRED：用户期望的 Pod 副本个数（spec.replicas 的值）；
        CURRENT：当前处于 Running 状态的 Pod 的个数；
        UP-TO-DATE：当前处于最新版本的 Pod 的个数，所谓最新版本指的是 Pod 的 Spec 部分与 Deployment 里 Pod 模板里定义的完全一致；
        AVAILABLE：当前已经可用的 Pod 的个数，即：既是 Running 状态，又是最新版本，并且已经处于 Ready（健康检查正确）状态的 Pod 的个数。
    
        可以看到，只有这个 AVAILABLE 字段，描述的才是用户所期望的最终状态。
    
        实时查看 Deployment 对象的状态变化。
         kubectl rollout status：
         
            $ kubectl rollout status deployment/nginx-deployment
            Waiting for rollout to finish: 2 out of 3 new replicas have been updated...
            deployment.apps/nginx-deployment successfully rolled out
        （返回结果中，“2 out of 3 new replicas have been updated”意味着已经有 2 个 Pod 进入了 UP-TO-DATE 状态。）
                
        继续等待，我们就能看到这个 Deployment 的 3 个 Pod，就进入到了 AVAILABLE 状态：        
            NAME               DESIRED   CURRENT   UP-TO-DATE   AVAILABLE   AGE
            nginx-deployment   3         3         3            3           20s            
                
        此时，你可以尝试查看一下这个 Deployment 所控制的 ReplicaSet：
        kubectl get rs            
            $ kubectl get rs
            NAME                          DESIRED   CURRENT   READY   AGE
            nginx-deployment-3167673210   3         3         3       20s
                
        在用户提交了一个 Deployment 对象后，Deployment Controller 就会立即创建一个 Pod 副本个数为 3 的 ReplicaSet
        （这个 ReplicaSet 的名字，则是由 Deployment 的名字和一个随机字符串共同组成。这个随机字符串叫作 pod-template-hash）
        
        ReplicaSet 的 DESIRED、CURRENT 和 READY 字段的含义，和 Deployment 中是一致的。
        可以发现Deployment 只是在 ReplicaSet 的基础上，添加了 UP-TO-DATE 这个跟版本有关的状态字段。            
            
            
    3、这个时候，如果我们修改了 Deployment 的 Pod 模板，“滚动更新”就会被自动触发

        使用 kubectl edit 指令编辑 Etcd 里的 API 对象：            
        
        $ kubectl edit deployment/nginx-deployment
        ... 
            spec:
              containers:
              - name: nginx
                image: nginx:1.9.1 # 1.7.9 -> 1.9.1
                ports:
                - containerPort: 80
        ...
        deployment.extensions/nginx-deployment edited
        
        kubectl edit 指令编辑完成后，保存退出，Kubernetes 就会立刻触发“滚动更新”的过程。
        （ kubectl rollout status）
        $ kubectl rollout status deployment/nginx-deployment
        Waiting for rollout to finish: 2 out of 3 new replicas have been updated...
        deployment.extensions/nginx-deployment successfully rolled out
        
        这时，你可以通过查看 Deployment 的 Events，看到这个“滚动更新”的流程：
        （通过kubectl describe 的Event字段查看）
        
        $ kubectl describe deployment nginx-deployment
        ...
        Events:
          Type    Reason             Age   From                   Message
          ----    ------             ----  ----                   -------
        ...
          Normal  ScalingReplicaSet  24s   deployment-controller  Scaled up replica set nginx-deployment-1764197365 to 1
          Normal  ScalingReplicaSet  22s   deployment-controller  Scaled down replica set nginx-deployment-3167673210 to 2
          Normal  ScalingReplicaSet  22s   deployment-controller  Scaled up replica set nginx-deployment-1764197365 to 2
          Normal  ScalingReplicaSet  19s   deployment-controller  Scaled down replica set nginx-deployment-3167673210 to 1
          Normal  ScalingReplicaSet  19s   deployment-controller  Scaled up replica set nginx-deployment-1764197365 to 3
          Normal  ScalingReplicaSet  14s   deployment-controller  Scaled down replica set nginx-deployment-3167673210 to 0
            
        可以看到执行了这些操作：
            1、当你修改了 Deployment 里的 Pod 定义之后，Deployment Controller 会使用这个修改后的 Pod 模板，创建一个新的 ReplicaSet（hash=1764197365），这个新的 ReplicaSet 的初始 Pod 副本数是：0。
    
            2、然后，在 Age=24 s 的位置，Deployment Controller 开始将这个新的 ReplicaSet 所控制的 Pod 副本数从 0 个变成 1 个，即：“水平扩展”出一个副本。

            3、在 Age=22 s 的位置，Deployment Controller 又将旧的 ReplicaSet（hash=3167673210）所控制的旧 Pod 副本数减少一个，即：“水平收缩”成两个副本。

            4、如此交替进行， 新 ReplicaSet 管理的 Pod 副本数，从 0 个变成3 个。旧的 ReplicaSet 管理的 Pod 副本数则从 3 个变成 0 个。这样，就完成了这一组 Pod 的版本升级过程。
    
        像这样，将一个集群中正在运行的多个 Pod 版本，交替地逐一升级的过程，就是“滚动更新”。
        
        在这个“滚动更新”过程完成之后，你可以查看一下新、旧两个 ReplicaSet 的最终状态：
            $ kubectl get rs
            NAME                          DESIRED   CURRENT   READY   AGE
            nginx-deployment-1764197365   3         3         3       6s		#新ReplicaSet
            nginx-deployment-3167673210   0         0         0       30s		#旧ReplicaSet

        滚动更新的好处：
        比如，在升级刚开始的时候，集群里只有 1 个新版本的 Pod。如果这时，新版本 Pod 有问题启动不起来，那么“滚动更新”就会停止，从而允许开发和运维人员介入。而在这个过程中，由于应用本身还有两个旧版本的 Pod 在线，所以服务并不会受到太大的影响。
        （当然，这也就要求你一定要使用 Pod 的 Health Check 机制检查应用的运行状态，而不是简单地依赖于容器的 Running 状态。要不然的话，虽然容器已经变成 Running 了，但服务很有可能尚未启动，“滚动更新”的效果也就达不到了。）
        
        而为了进一步保证服务的连续性，Deployment Controller 还会确保，在任何时间窗口内，只有指定比例的 Pod 处于离线状态。同时，它也会确保，在任何时间窗口内，只有指定比例的新 Pod 被创建出来。这两个比例的值都是可以配置的，默认都是 DESIRED 值的 25%。
        
所以，在上面这个 Deployment 的例子中，它有 3 个 Pod 副本，那么控制器在“滚动更新”的过程中永远都会确保至少有 2 个 Pod 处于可用状态，至多只有 4 个 Pod 同时存在于集群中。这个策略，是 Deployment 对象的一个字段，名叫 RollingUpdateStrategy，如下所示：                
    
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: nginx-deployment
      labels:
        app: nginx
    spec:
    ...
      strategy:
        type: RollingUpdate
        rollingUpdate:
          maxSurge: 1
          maxUnavailable: 1
                  
在上面这个 RollingUpdateStrategy 的配置中，
maxSurge 指定的是除了 DESIRED 数量之外，在一次“滚动”中，Deployment 控制器还可以创建多少个新 Pod；
maxUnavailable 指的是，在一次“滚动”中，Deployment 控制器可以删除多少个旧 Pod。
（一次滚动）
        
（这两个配置还可以用前面我们介绍的百分比形式来表示，比如：maxUnavailable=50%，指的是我们最多可以一次删除“50%*DESIRED 数量”个 Pod。）

（Deployment 的控制器，实际上控制的是 ReplicaSet 的数目，以及每个 ReplicaSet 的属性。）
即：“应用版本和 ReplicaSet 一一对应”的设计思想
    
Deployment 对应用进行版本控制的具体原理：
kubectl set image 的指令，直接修改 nginx-deployment 所使用的镜像。这个命令的好处就是，你可以不用像 kubectl edit 那样需要打开编辑器。

（把这个镜像名字修改成为了一个错误的名字，比如：nginx:1.91。这样，这个 Deployment 就会出现一个升级失败的版本。）            
        
    $ kubectl set image deployment/nginx-deployment nginx=nginx:1.91
    deployment.extensions/nginx-deployment image updated            
            
由于这个 nginx:1.91 镜像在 Docker Hub 中并不存在，所以这个 Deployment 的“滚动更新”被触发后，会立刻报错并停止。
    
    $ kubectl get rs
    NAME                          DESIRED   CURRENT   READY   AGE
    nginx-deployment-1764197365   2         2         2       24s
    nginx-deployment-3167673210   0         0         0       35s
    nginx-deployment-2156724341   2         2         0       7s            
            
通过这个返回结果，我们可以看到，新版本的 ReplicaSet（hash=2156724341）的“水平扩展”已经停止。而且此时，它已经创建了两个 Pod，但是它们都没有进入 READY 状态。这当然是因为这两个 Pod 都拉取不到有效的镜像。
与此同时，旧版本的 ReplicaSet（hash=1764197365）的“水平收缩”，也自动停止了。此时，已经有一个旧 Pod 被删除，还剩下两个旧 Pod。
        
        
目标1：让这个Deployment的3个Pod 都回滚到以前的旧版本

只需要执行一条 kubectl rollout undo 命令，就能把整个 Deployment 回滚到上一个版本：    
        
    $ kubectl rollout undo deployment/nginx-deployment
    deployment.extensions/nginx-deployment            
                        
在具体操作上：其实就是让这个旧 ReplicaSet（hash=1764197365）再次“扩展”成 3 个 Pod，而让新的 ReplicaSet（hash=2156724341）重新“收缩”到 0 个 Pod。
    
目标2：回滚到更早之前的版本

    1、使用 kubectl rollout history 命令，查看每次 Deployment 变更对应的版本。
    （由于我们在创建这个 Deployment 的时候，指定了–record 参数，所以我们创建这些版本时执行的 kubectl 命令，都会被记录下来。）            
        
    在具体操作上：其实就是让这个旧 ReplicaSet（hash=1764197365）再次“扩展”成 3 个 Pod，而让新的 ReplicaSet（hash=2156724341）重新“收缩”到 0 个 Pod。
        $ kubectl rollout history deployment/nginx-deployment
        deployments "nginx-deployment"
        REVISION    CHANGE-CAUSE
        1           kubectl create -f nginx-deployment.yaml --record
        2           kubectl edit deployment/nginx-deployment
        3           kubectl set image deployment/nginx-deployment nginx=nginx:1.91
        
        #（可以指定版本查看Deployment的API对象的细节）：
        $ kubectl rollout history deployment/nginx-deployment --revision=2
    2、在 kubectl rollout undo 命令行最后，加上要回滚到的指定版本的版本号，就可以回滚到指定版本了。
        kubectl rollout undo  deployment/deployment-name  --to-revision=revision-num
        
        $ kubectl rollout undo deployment/nginx-deployment --to-revision=2
        deployment.extensions/nginx-deployment   
    
    这样，Deployment Controller 还会按照“滚动更新”的方式，完成对 Deployment 的降级操作。(一扩一缩）

        
        
总结：

Deployment 实际上是一个两层控制器。首先，它通过 ReplicaSet 的个数来描述应用的版本；然后，它再通过 ReplicaSet 的属性（比如 replicas 的值），来保证 Pod 的副本数量。
    （Deployment 控制 ReplicaSet（版本），ReplicaSet 控制 Pod（副本数）。这个两层控制关系一定要牢记。）
        使用 kubectl rollout 命令控制应用的版本

滚动更新（自动化更新的金丝雀发布）

金丝雀部署：优先发布一台或少量机器升级，等验证无误后再更新其他机器。优点是用户影响范围小，不足之处是要额外控制如何做自动更新。

蓝绿部署：2组机器，蓝代表当前的V1版本，绿代表已经升级完成的V2版本。通过LB将流量全部导入V2完成升级部署。优点是切换快速，缺点是影响全部用户。
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
            