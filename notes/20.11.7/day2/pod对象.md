能把 Pod 看成传统环境里的“机器”、把容器看作是运行在这个“机器”里的“用户程序”，那么很多关于 Pod 对象的设计就非常容易理解了。

比如，凡是调度、网络、存储，以及安全相关的属性，基本上是 Pod 级别的。

 

Pod 中几个重要字段的含义和用法：

 

一、跟机器相关的属性配置

1.      NodeSelector：是一个供用户将 Pod 与 Node 进行绑定的字段 （把Pod绑定在Node上）

用法如下：

apiVersion: v1
kind: Pod
...
spec:
 nodeSelector:
   disktype: ssd


这样一个配置，以为这这个Pod永远只能运行在携带了 "disktype:ssd" 标签（Label）的节点上；否则它将调度失败

 

2、NodeName：一旦 Pod 的这个字段被赋值，Kubernetes 项目就会被认为这个 Pod 已经经过了调度，调度的结果就是赋值的节点名字。

所以，这个字段一般由调度器负责设置，但用户也可以设置它来“骗过”调度器，当然这个做法一般是在测试或者调试的时候才会用到。

 

3、HostAliases：定义了 Pod 的 hosts 文件（比如 /etc/hosts）里的内容

 apiVersion: v1
kind: Pod
...
spec:
  hostAliases:
  - ip: "10.1.2.3"
    hostnames:
    - "foo.remote"
    - "bar.remote"
...

 

如上：

这个Pod的YAML文件中，设置了一组IP和hostname的数据。这样，这个Pod启动后，/etc/hosts文件的内容将如下所示：

 cat /etc/hosts
# Kubernetes-managed hosts file.
127.0.0.1 localhost
...
10.244.135.10 hostaliases-pod
10.1.2.3 foo.remote
10.1.2.3 bar.remote

其中，最下面两行记录，就是我通过 HostAliases 字段为 Pod 设置的。需要指出的是，在 Kubernetes 项目中，如果要设置 hosts 文件里的内容，一定要通过这种方法。否则，如果直接修改了 hosts 文件的话，在 Pod 被删除重建之后，kubelet 会自动覆盖掉被修改的内容。

 

二、跟容器的Linux Namespace相关的属性

除了上述跟“机器”相关的配置外，你可能也会发现，凡是跟容器的 Linux Namespace 相关的属性，也一定是 Pod 级别的

原因：Pod 的设计，就是要让它里面的容器尽可能多地共享 Linux Namespace，仅保留必要的隔离和限制能力。这样，Pod 模拟出的效果，就跟虚拟机里程序间的关系非常类似了。

 

例如：

在下面这个 Pod 的 YAML 文件中，我定义了 shareProcessNamespace=true：

 apiVersion: v1
kind: Pod
metadata:
  name: nginx
spec:
  shareProcessNamespace: true
  containers:
  - name: nginx
    image: nginx
  - name: shell
    image: busybox
    stdin: true
    tty: true

这就意味着这个 Pod 里的容器要共享 PID Namespace

在这个YAML文件中，还定义了两个容器：一个是nginx容器，一个是开启了tty和stdin 的shell容器

在YAML文件里声明开启它们俩，等同于设置了docker run 里的 -it（ -i 即stdin，-t 即tty）参数。

这样，这个Pod被创建后，就可以使用shell容器的tty跟这个容器进行交互了

 

实践：

$ kubectl create -f nginx.yaml

使用kubectl attach 连接到shell容器的tty上：

kubectl attach -it nginx -c shell

 
这样就可以在shell容器里执行命令

如：

$ kubectl attach -it nginx -c shell
/ # ps ax
PID   USER     TIME  COMMAND
    1 root      0:00 /pause
    8 root      0:00 nginx: master process nginx -g daemon off;
   14 101       0:00 nginx: worker process
   15 root      0:00 sh
   21 root      0:00 ps ax

可以看到，在这个容器里，我们不仅可以看到它本身的 ps ax 指令，还可以看到 nginx 容器的进程，以及 Infra 容器的 /pause 进程。这就意味着，整个 Pod 里的每个容器的进程，对于所有容器来说都是可见的：它们共享了同一个 PID Namespace。（YAML文件中定义的）

类似地，凡是 Pod 中的容器要共享宿主机的 Namespace，也一定是 Pod 级别的定义

如：

 apiVersion: v1
kind: Pod
metadata:
  name: nginx
spec:
  hostNetwork: true
  hostIPC: true
  hostPID: true
  containers:
  - name: nginx
    image: nginx
  - name: shell
    image: busybox
    stdin: true
    tty: true

在这个 Pod 中，我定义了共享宿主机的 Network 、IPC 和 PID Namespace（上面6，7，8行）。这就意味着，这个 Pod 里的所有容器，会直接使用宿主机的网络、直接与宿主机进行 IPC 通信、看到宿主机里正在运行的所有进程。

 

 

三、Containers字段

“Containers”、“Init Containers”  这两个字段都属于 Pod 对容器的定义，内容也完全相同，只是 Init Containers 的生命周期，会先于所有的 Containers，并且严格按照定义的顺序执行。

 

①、ImagePullPolicy字段定义了镜像拉取的策略。而它之所以是一个 Container 级别的属性，是因为容器镜像本来就是 Container 定义中的一部分

Defaults to Always if :latest tag is specified, or IfNotPresent otherwise

如果指定了：latest标签，默认为Always，否则为IfNotPresent  (只在宿主机上不存在这个镜像时才拉取)

 

②、Lifecycle字段，它定义的是 Container Lifecycle Hooks。顾名思义，Container Lifecycle Hooks 的作用，是在容器状态发生变化时触发一系列“钩子”。我们来看这样一个例子：

apiVersion: v1
kind: Pod
metadata:
  name: lifecycle-demo
spec:
  containers:
  - name: lifecycle-demo-container
    image: nginx
    lifecycle:
      postStart:
        exec:
          command: ["/bin/sh", "-c", "echo Hello from the postStart handler > /usr/share/message"]
      preStop:
        exec:
          command: ["/usr/sbin/nginx","-s","quit"]


（postStart和preStop）

postStart:容器启动后，立刻执行一个指定的操作

需要明确的是，postStart 定义的操作，虽然是在 Docker 容器     ENTRYPOINT 执行之后，但它并不严格保证顺序。也就是说，在 postStart 启动时，ENTRYPOINT 有可能还没有结束。

如果 postStart 执行超时或者错误，Kubernetes 会在该 Pod 的 Events 中报出该容器启动失败的错误信息，导致 Pod 也处于失败的状态。

 

preStop: 发生在容器被杀死之前（比如收到了SIGKILL信号）

需要明确的是，preStop操作的执行，是同步的。所以它会阻塞当前容器杀死流程，知道这个Hook定义操作完成之后，才允许容器被杀死，这个postStart不一样

 

POD对象在K8S中的生命周期

Pod 生命周期的变化，主要体现在 Pod API 对象的 Status部分，这是它除了 Metadata和 Spec之外的第三个重要字段。其 中，pod.status.phase，就是Pod 的当前状态，它有如下几种可能的情况：

	Pending。这个状态意味着，Pod 的 YAML 文件已经提交给了 Kubernetes，API 对象已经被创建并保存在 Etcd 当中。但是，这个 Pod 里有些容器因为某种原因而不能被顺利创建。比如，调度不成功。

	Running。这个状态下，Pod 已经调度成功，跟一个具体的节点绑定。它包含的容器都已经创建成功，并且至少有一个正在运行中。

	Succeeded。这个状态意味着，Pod 里的所有容器都正常运行完毕，并且已经退出了。这种情况在运行一次性任务时最为常见。

	Failed。这个状态下，Pod 里至少有一个容器以不正常的状态（非 0 的返回码）退出。这个状态的出现，意味着你得想办法 Debug 这个容器的应用，比如查看 Pod 的 Events 和日志。

	Unknown。这是一个异常状态，意味着 Pod 的状态不能持续地被 kubelet 汇报给 kube-apiserver，这很有可能是主从节点（Master 和 Kubelet）间的通信出现了问题。

 