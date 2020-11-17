PV 是持久化存储数据卷。这个API对象主要定义的是一个持久化存储在宿主机上的目录，比如一个NFS的挂载目录。

PV对象通常由运维人员事先创建在K8S集群里待用的

比如，运维人员可以定义这样一个 NFS 类型的 PV，如下所示：

    apiVersion: v1
    kind: PersistentVolume
    metadata:
      name: nfs
    spec:
      storageClassName: manual
      capacity:
        storage: 1Gi
      accessModes:
        - ReadWriteMany
      nfs:
        server: 10.244.1.4
        path: "/"


PVC是Pod所希望使用的持久化存储的属性。比如Volume存储的大小、可读写权限等等。PVC对象通常由开发人员创建；或者以


PVC模板的方式成为StatefulSet的一部分，然后由StatefulSet控制器负责创建带编号的PVC


比如，开发人员可以声明一个 1 GiB 大小的 PVC，如下所示：

    apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      name: nfs
    spec:
      accessModes:
        - ReadWriteMany
      storageClassName: manual
      resources:
        requests:
          storage: 1Gi


用户创建的PVC要被容器用起来，首先要和某个符合条件的PV进行绑定

这里检查的条件，包括两部分：

    1、第一个条件，当然是 PV 和 PVC 的 spec 字段。比如，PV 的存储（storage）大小，就必须满足 PVC 的要求。
    2、第二个条件，是 PV 和 PVC 的 storageClassName 字段必须一样


成功将PVC和PV进行绑定后，Pod就能像使用hostPath等常规类型的Volume一样，在yaml文件中声明使用这个PVC了

如：

    apiVersion: v1
    kind: Pod
    metadata:
      labels:
        role: web-frontend
    spec:
      containers:
      - name: web
        image: nginx
        ports:
          - name: web
            containerPort: 80
        volumeMounts:
            - name: nfs
              mountPath: "/usr/share/nginx/html"
      volumes:
      - name: nfs
        persistentVolumeClaim:
          claimName: nfs

（Pod只要在volumes字段中声明自己要使用的PVC的名字，等这个Pod创建之后，kubelet就会把这个PVC对应的PV，挂载在这个容器的目录里）


类比“面向对象”思想

    PVC：接口
    PV：具体实现


#问题：开发人员创建Pod的时候，系统里没有匹配的PV与Pod定义的PVC绑定，会报错


专门处理持久化存储的控制器：Volume Controlle


循环：不断查看当前的每一个PVC是否已经处于Bound（已绑定）状态，如果不是，就会遍历所有的、可用的PV，尝试与这个PVC进行绑定
（绑定，：将这个PV对象的名字，填在了PVC对象的spec.volumeName字段上）


如何实现的？

这个 PV 对象，是如何变成容器里的一个持久化存储的？


“持久化 Volume”，指的就是这个宿主机上的目录，具备“持久性”

持久化 Volume 的实现，往往依赖于一个远程存储服务，比如：远程文件存储（比如，NFS、GlusterFS）、远程块存储（比如，公有云提供的远程磁盘）等

而 Kubernetes 需要做的工作，就是使用这些存储服务，来为容器准备一个持久化的宿主机目录，以供将来进行绑定挂载时使用。而所谓“持久化”，指的是容器在这个目录里写入的文件，都会保存在远程存储中，从而使得这个目录具备了“持久性”。

这个准备“持久化”宿主机目录的过程，我们可以形象地称为“两阶段处理”。


    1、当一个 Pod 调度到一个节点上之后，kubelet 就要负责为这个 Pod 创建它的 Volume 目录。
    （默认情况下，kubelet 为 Volume 创建的目录是如下所示的一个宿主机上的路径：
    
        /var/lib/kubelet/pods/<Pod的ID>/volumes/kubernetes.io~<Volume类型>/<Volume名字>）
    
    
    2、接下来，kubelet 要做的操作就取决于你的 Volume 类型了。
    如果你的 Volume 类型是远程块存储

    将远程磁盘挂载到宿主机上
    那么 kubelet 就需要先调用 Goolge Cloud 的 API，将它所提供的 Persistent Disk 挂载到 Pod 所在的宿主机上。
    
    相当于执行：
    
        $ gcloud compute instances attach-disk <虚拟机名字> --disk <远程磁盘名字>
    
    这一步为虚拟机挂载远程磁盘的操作，对应的正是“两阶段处理”的第一阶段。在 Kubernetes 中，我们把这个阶段称为 Attach。


    Attach完成之后，为了能够使用这个远程磁盘，kubelet 还要进行第二个操作：
    
    格式化这个磁盘设备，然后将它挂载到宿主机指定的挂载点上。

        # 通过lsblk命令获取磁盘设备ID
        $ sudo lsblk
        # 格式化成ext4格式
        $ sudo mkfs.ext4 -m 0 -F -E lazy_itable_init=0,lazy_journal_init=0,discard /dev/<磁盘设备ID>
            
        # 挂载到挂载点
        $ sudo mkdir -p /var/lib/kubelet/pods/<Pod的ID>/volumes/kubernetes.io~<Volume类型>/<Volume名字>
    
    将磁盘设备格式化并挂载到 Volume 宿主机目录的操作，对应的正是“两阶段处理”的第二个阶段，我们一般称为：Mount。



如果Volume的类型是远程文件存储（比如NFS）的话，kubelet就会跳过第一阶段（远程文件存储并不需要挂载“存储设备”到宿主机上）


kubelet 会直接从“第二阶段”（Mount）开始准备宿主机上的 Volume 目录。在这一步，kubelet 需要作为 client，将远端 NFS 服务器的目录（比如：“/”目录），挂载到 Volume 的宿主机目录上，即相当于执行如下所示的命令：

    $ mount -t nfs <NFS服务器地址>:/ /var/lib/kubelet/pods/<Pod的ID>/volumes/kubernetes.io~<Volume类型>/<Volume名字> 


K8S是如何区分这两个阶段的？

在具体的Volume插件的实现接口上，K8S分别给这两个阶段提供了两种不同的参数列表

    对于“第一阶段”（Attach），Kubernetes 提供的可用参数是 nodeName，即宿主机的名字。
    对于“第二阶段”（Mount），Kubernetes 提供的可用参数是 dir，即 Volume 的宿主机目录。


经过了“两阶段处理”，我们就得到了一个“持久化”的 Volume 宿主机目录


接下来，kubelet 只要把这个 Volume 目录通过 CRI 里的 Mounts 参数，传递给 Docker，然后就可以为 Pod 里的容器挂载这个“持久化”的 Volume 了。


其实，这一步相当于执行了如下所示的命令：

    $ docker run -v /var/lib/kubelet/pods/<Pod的ID>/volumes/kubernetes.io~<Volume类型>/<Volume名字>:/<容器内的目标目录> 我的镜像 


kubelet 在向 Docker 发起 CRI 请求之前，确保“持久化”的宿主机目录已经处理完毕即可。

所以，在 Kubernetes 中，上述关于 PV 的“两阶段处理”流程，是靠独立于 kubelet 主控制循环（Kubelet Sync Loop）之外的两个控制循环来实现的。


    “第一阶段”的 Attach（以及 Dettach）操作，是由 Volume Controller 负责维护的，这个控制循环的名字叫作：AttachDetachController。
    （作用是不断地检查每一个Pod对应的PV，和这个Pod所在宿主机之间挂载情况。从而决定是否需要对这个PV进行Attach操作）
    
    （作为K8S内置的控制器，Volume Controller自然也是kube-controller-manager的一部分，所以，AttachDetachController 也一定是运行在 Master 节点上的。）
    
    “第二阶段”的 Mount（以及 Unmount）操作，必须发生在 Pod 对应的宿主机上，所以它必须是 kubelet 组件的一部分。这个控制循环的名字，叫作：VolumeManagerReconciler，它运行起来之后，是一个独立于 kubelet 主循环的 Goroutine。
    
    通过这样将 Volume 的处理同 kubelet 的主循环解耦，Kubernetes 就避免了这些耗时的远程挂载操作拖慢 kubelet 的主控制循环，进而导致 Pod 的创建效率大幅下降的问题。实际上，kubelet 的一个主要设计原则，就是它的主控制循环绝对不可以被 block。




StorageClass


大规模生产中，需要自动创建PV才能满足需求


StorageClass 对象的作用，是创建 PV 的模板。



具体地说，StorageClass 对象会定义如下两个部分内容：


第一，PV 的属性。比如，存储类型、Volume 的大小等等。
第二，创建这种 PV 需要用到的存储插件。比如，Ceph 等等。



有了这两个信息，K8S就能通过用户提交的PVC找到一个对应的StorageClass，然后，Kubernetes 就会调用该 StorageClass 声明的存储插件，创建出需要的 PV。


1、创建一个StorageClass

    apiVersion: ceph.rook.io/v1beta1
    kind: Pool
    metadata:
      name: replicapool
      namespace: rook-ceph
    spec:
      replicated:
        size: 3
    ---
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: block-service
    provisioner: ceph.rook.io/block
    parameters:
      pool: replicapool
      #The value of "clusterNamespace" MUST be the same as the one in which your rook cluster exist
      clusterNamespace: rook-ceph


2、创建PVC（指定要使用的StorageClass的名字）

    apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      name: claim1
    spec:
      accessModes:
        - ReadWriteOnce
      storageClassName: block-service
      resources:
        requests:
          storage: 30Gi


3、K8S会自动创建PV

（并且个自动创建出来的 PV 的 StorageClass 字段的值，也是 block-service。这是因为，Kubernetes 只会将 StorageClass 相同的 PVC 和 PV 绑定起来。即使是手动创建，也会考虑PV和PVC的StorageClass定义）




因此，只需要在K8S中创建StorageClass对象（就相当于PV模板）




#总结

    1、用户提交请求创建pod，Kubernetes发现这个pod声明使用了PVC，那就靠PersistentVolumeController帮它找一个PV配对。
    
    2、没有现成的PV，就去找对应的StorageClass，帮它新创建一个PV，然后和PVC完成绑定。
    
    3、新创建的PV，还只是一个API 对象，需要经过“两阶段处理”变成宿主机上的“持久化 Volume”才真正有用：
    
    第一阶段由运行在master上的AttachDetachController负责，为这个PV完成 Attach 操作，为宿主机挂载远程磁盘；
    第二阶段是运行在每个节点上kubelet组件的内部，把第一步attach的远程磁盘 mount 到宿主机目录。这个控制循环叫VolumeManagerReconciler，运行在独立的Goroutine，不会阻塞kubelet主循环。
    
    完成这两步，PV对应的“持久化 Volume”就准备好了，POD可以正常启动，将“持久化 Volume”挂载在容器内指定的路径。










