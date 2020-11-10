Kubernetes 项目引入了一组叫作 Persistent Volume Claim（PVC）和 Persistent Volume（PV）的 API 对象，大大降低了用户声明和使用持久化 Volume 的门槛。

有了 PVC 之后，一个开发人员想要使用一个 Volume，只需要简单的两步即可。

第一步：定义一个 PVC，声明想要的 Volume 的属性：

    kind: PersistentVolumeClaim
    apiVersion: v1
    metadata:
      name: pv-claim
    spec:
      accessModes:
      - ReadWriteOnce
      resources:
        requests:
          storage: 1Gi

在这个 PVC 对象里，不需要任何关于 Volume 细节的字段，只有描述性的属性和定义。

比如：

    storage: 1Gi：表示我想要的 Volume 大小至少是 1 GiB；
    
    accessModes: ReadWriteOnce：表示这个 Volume 的挂载方式是可读写，并且只能被挂载在一个节点上而非被多个节点共享。


第二步：在应用的 Pod 中，声明使用这个 PVC：

    apiVersion: v1
    kind: Pod
    metadata:
      name: pv-pod
    spec:
      containers:
        - name: pv-container
          image: nginx
          ports:
            - containerPort: 80
              name: "http-server"
          volumeMounts:
            - mountPath: "/usr/share/nginx/html"
              name: pv-storage
      volumes:
        - name: pv-storage
          persistentVolumeClaim:
            claimName: pv-claim

可以看到，在这个 Pod 的 Volumes 定义中，我们只需要声明它的类型是 persistentVolumeClaim，然后指定 PVC 的名字，而完全不必关心 Volume 本身的定义。

这时候，只要我们创建这个 PVC 对象，Kubernetes 就会自动为它绑定一个符合条件的 Volume。

这些符合条件的 Volume 又是从哪里来的呢？
    
    来自于由运维人员维护的 PV（Persistent Volume）对象。

常见的 PV 对象的 YAML 文件：

    kind: PersistentVolume
    apiVersion: v1
    metadata:
      name: pv-volume
      labels:
        type: local
    spec:
      capacity:
        storage: 10Gi
      accessModes:
        - ReadWriteOnce
      rbd:
        monitors:
        # 使用 kubectl get pods -n rook-ceph 查看 rook-ceph-mon- 开头的 POD IP 即可得下面的列表
        - '10.16.154.78:6789'
        - '10.16.154.82:6789'
        - '10.16.154.83:6789'
        pool: kube
        image: foo
        fsType: ext4
        readOnly: true
        user: admin
        keyring: /etc/ceph/keyring

可以看到，这个 PV 对象的 spec.rbd 字段，正是我们前面介绍过的 Ceph RBD Volume 的详细定义。而且，它还声明了这个 PV 的容量是 10 GiB。这样，Kubernetes 就会为我们刚刚创建的 PVC 对象绑定这个 PV。

    PVC：接口
    PV：实现

PVC、PV 的设计，也使得 StatefulSet 对存储状态的管理成为了可能：

以StatefulSet为例

    apiVersion: apps/v1
    kind: StatefulSet
    metadata:
      name: web
    spec:
      serviceName: "nginx"
      replicas: 2
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
            image: nginx:1.9.1
            ports:
            - containerPort: 80
              name: web
            volumeMounts:
            - name: www
              mountPath: /usr/share/nginx/html
      volumeClaimTemplates:
      - metadata:
          name: www
        spec:
          accessModes:
          - ReadWriteOnce
          resources:
            requests:
              storage: 1Gi

我们为这个 StatefulSet 额外添加了一个 volumeClaimTemplates 字段。从名字就可以看出来，它跟 Deployment 里 Pod 模板（PodTemplate）的作用类似。

也就是说，凡是被这个 StatefulSet 管理的 Pod，都会声明一个对应的 PVC；而这个 PVC 的定义，就来自于 volumeClaimTemplates 这个模板字段。

更重要的是，这个 PVC 的名字，会被分配一个与这个 Pod 完全一致的编号。





















































































