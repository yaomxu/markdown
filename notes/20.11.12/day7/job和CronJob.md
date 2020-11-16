Deployment、StatefulSet，以及 DaemonSet 这三个编排概念的主要编排的对象，都是“在线业务”，Long Running Task （长作业）  比如，常用的 Nginx、Tomcat，以及 MySQL 等等，这些应用一旦运行起来，除非出错或者停止，它的容器进程会一直保持在 Running 状态。

而“离线业务”，或者叫作 Batch Job（计算业务）。这种业务在计算完成后就直接退出了，而此时如果你依然用 Deployment 来管理这种业务的话，就会发现 Pod 会在计算结束后退出，然后被 Deployment Controller 不断地重启；而像“滚动更新”这样的编排功能，更无从谈起了。

LRS：Deployment、StatefulSet、DaemonSet
Batch Job: Job、CronJob


Job API对象：

    apiVersion: batch/v1
    kind: Job
    metadata:
      name: pi
    spec:
      template:
        spec:
          containers:
          - name: pi
            image: resouer/ubuntu-bc 
            command: ["sh", "-c", "echo 'scale=10000; 4*a(1)' | bc -l "]
          restartPolicy: Never
      backoffLimit: 4


这个例子中定义了 restartPolicy=Never，那么离线作业失败后 Job Controller 就会不断地尝试创建一个新 Pod

（spec.backoffLimit 字段里定义了重试次数为 4（即，backoffLimit=4），而这个字段的默认值是 6）
（Job Controller 重新创建 Pod 的间隔是呈指数增加的，即下一次重新创建 Pod 的动作会分别发生在 10 s、20 s、40 s …后。）


如果你定义的 restartPolicy=OnFailure，那么离线作业失败后，Job Controller 就不会去尝试创建新的 Pod。但是，它会不断地尝试重启 Pod 里的容器



一个Job的Pod运行结束后，它会进入Completed状态。

但是，如果这个Pod因为某种原因一直不肯结束呢？

在Job的API对象里，有一个spec.activeDeadlineSeconds字段可以设置最长运行时间，如：

    spec:
     backoffLimit: 5
     activeDeadlineSeconds: 100
     
一旦运行超过了100s，这个Job所有的Pod都会被终止

并且，你可以在 Pod 的状态里看到终止的原因是 reason: DeadlineExceeded



BatchJob，并行方式运行
在 Job 对象中，负责并行控制的参数有两个：

    1、spec.parallelism，它定义的是一个 Job 在任意时间最多可以启动多少个 Pod 同时运行；（最大并行数）
    
    2、spec.completions，它定义的是 Job 至少要完成的 Pod 数目，即 Job 的最小完成数。（最小完成数）

在前面计算Pi值的Job里，添加两个参数：

    apiVersion: batch/v1
    kind: Job
    metadata:
      name: pi
    spec:
      parallelism: 2
      completions: 4
      template:
        spec:
          containers:
          - name: pi
            image: resouer/ubuntu-bc
            command: ["sh", "-c", "echo 'scale=5000; 4*a(1)' | bc -l "]
          restartPolicy: Never
      backoffLimit: 4
      
这样，我们就指定了这个 Job 最大的并行数是 2，而最小的完成数是 4。


kubectl create -f job.yaml
kubectl get job
kubectl get pods


    Job Controller 控制的对象，直接就是 Pod
    Job Controller 在控制循环中进行的调谐（Reconcile）操作，是根据实际在 Running 状态 Pod 的数目、已经成功退出的 Pod 的数目，以及 parallelism、completions 参数的值共同计算出在这个周期里，应该创建或者删除的 Pod 数目，然后调用 Kubernetes API 来执行这个操作。


原理：

    1、Job一开始创建出来
    
    2、处于Running的Pod数目=0，成功退出的 Pod 数目=0
    
    3、而用户定义的 completions，也就是最终用户需要的 Pod 数目 =4
    
    4、所以这时，需要创建的 Pod 数目 = 最终需要的 Pod 数目 - 实际在 Running 状态 Pod 数目 - 已经成功退出的 Pod 数目 = 4 - 0 - 0= 4，即Job Controller 需要创建 4 个 Pod 来纠正这个不一致状态
    
    5、这时发现这个 Job 的 parallelism=2，即规定了每次并发创建的 Pod 个数不能超过 2 个，所以，Job Controller 会对前面的计算结果做一个修正，修正后的期望创建的 Pod 数目应该是：2 个。

    6、这时候，Job Controller 就会并发地向 kube-apiserver 发起两个创建 Pod 的请求。

    （类似地，如果在这次调谐周期里，Job Controller 发现实际在 Running 状态的 Pod 数目，比 parallelism 还大，那么它就会删除一些 Pod，使两者相等。）


三种常用的使用Job对象的方法：


第一种用法，也是最简单粗暴的用法：外部管理器 +Job 模板

        把Job的YAML文件定义成一个模板，然后用一个外部工具控制这些模板来生成Job    
        如：
            apiVersion: batch/v1
            kind: Job
            metadata:
              name: process-item-$ITEM
              labels:
                jobgroup: jobexample
            spec:
              template:
                metadata:
                  name: jobexample
                  labels:
                    jobgroup: jobexample
                spec:
                  containers:
                  - name: c
                    image: busybox
                    command: ["sh", "-c", "echo Processing item $ITEM && sleep 5"]
                  restartPolicy: Never
        在这个Job的YAML中，定义了$ITEM这样的变量
        在控制这种 Job 时，我们只要注意如下两个方面即可：
        创建 Job 时，替换掉 $ITEM 这样的变量；
        所有来自于同一个模板的 Job，都有一个 jobgroup: jobexample 标签，也就是说这一组 Job 使用这样一个相同的标识。
        
        
        通过shell把 $ITEM 替换掉 生成统一模板的不同Job的yaml 再通过kubectl create 生成
        如
            $ mkdir ./jobs
            $ for i in apple banana cherry
            do
              cat job-tmpl.yaml | sed "s/\$ITEM/$i/" > ./jobs/job-$i.yaml
            done
            
            $ kubectl create -f ./jobs
            $ kubectl get pods -l jobgroup=jobexample
            NAME                        READY     STATUS      RESTARTS   AGE
            process-item-apple-kixwv    0/1       Completed   0          4m
            process-item-banana-wrsf7   0/1       Completed   0          4m
            process-item-cherry-dnfu9   0/1       Completed   0          4m


第二种用法：拥有固定任务数目的并行 Job

    这种模式下，我只关心最后是否有指定数目（spec.completions）个任务成功退出。至于执行时的并行度是多少，我并不关心。
    
    使用工作队列（Work Queue）进行任务分发
    
        apiVersion: batch/v1
        kind: Job
        metadata:
          name: job-wq-1
        spec:
          completions: 8
          parallelism: 2
          template:
            metadata:
              name: job-wq-1
            spec:
              containers:
              - name: c
                image: myrepo/job-wq-1
                env:
                - name: BROKER_URL
                  value: amqp://guest:guest@rabbitmq-service:5672
                - name: QUEUE
                  value: job1
              restartPolicy: OnFailure

    我们可以看到，它的 completions 的值是：8，这意味着我们总共要处理的任务数目是 8 个。也就是说，总共会有 8 个任务会被逐一放入工作队列里（你可以运行一个外部小程序作为生产者，来提交任务）。
    
    在这个实例中，我选择充当工作队列的是一个运行在 Kubernetes 里的 RabbitMQ。所以，我们需要在 Pod 模板里定义 BROKER_URL，来作为消费者。
    
    所以，一旦你用 kubectl create 创建了这个 Job，它就会以并发度为 2 的方式，每两个 Pod 一组，创建出 8 个 Pod。每个 Pod 都会去连接 BROKER_URL，从 RabbitMQ 里读取任务，然后各自进行处理。这个 Pod 里的执行逻辑，我们可以用这样一段伪代码来表示：

        /* job-wq-1的伪代码 */
        queue := newQueue($BROKER_URL, $QUEUE)
        task := queue.Pop()
        process(task)
        exit


    可以看到，每个 Pod 只需要将任务信息读取出来，处理完成，然后退出即可。而作为用户，我只关心最终一共有 8 个计算任务启动并且退出，只要这个目标达到，我就认为整个 Job 处理完成了。所以说，这种用法，对应的就是“任务总数固定”的场景。


第三种用法，也是很常用的一个用法：指定并行度（parallelism），但不设置固定的 completions 的值。

    自己来决定什么时候启动新 Pod，什么时候 Job 才算执行完成。
    
    在这种情况下，任务的总数是未知的，所以你不仅需要一个工作队列来负责任务分发，还需要能够判断工作队列已经为空（即：所有的工作已经结束了）。
    
    （指定并行数）
        apiVersion: batch/v1
        kind: Job
        metadata:
          name: job-wq-2
        spec:
          parallelism: 2
          template:
            metadata:
              name: job-wq-2
            spec:
              containers:
              - name: c
                image: gcr.io/myproject/job-wq-2
                env:
                - name: BROKER_URL
                  value: amqp://guest:guest@rabbitmq-service:5672
                - name: QUEUE
                  value: job2
              restartPolicy: OnFailure
        /* job-wq-2的伪代码 */
        for !queue.IsEmpty($BROKER_URL, $QUEUE) {
          task := queue.Pop()
          process(task)
        }
        print("Queue empty, exiting")
        exit
    由于任务数目的总数不固定，所以每一个 Pod 必须能够知道，自己什么时候可以退出。比如，在这个例子中，我简单地以“队列为空”，作为任务全部完成的标志。所以说，这种用法，对应的是“任务总数不固定”的场景。
    不过，在实际的应用中，你需要处理的条件往往会非常复杂。比如，任务完成后的输出、每个任务 Pod 之间是不是有资源的竞争和协同等等。
    所以，在今天这篇文章中，我就不再展开 Job 的用法了。因为，在实际场景里，要么干脆就用第一种用法来自己管理作业；要么，这些任务 Pod 之间的关系就不那么“单纯”，甚至还是“有状态应用”（比如，任务的输入 / 输出是在持久化数据卷里）。在这种情况下，我在后面要重点讲解的 Operator，加上 Job 对象一起，可能才能更好地满足实际离线任务的编排需求。




CronJob
API对象：

    apiVersion: batch/v1beta1
    kind: CronJob
    metadata:
      name: hello
    spec:
      schedule: "*/1 * * * *"
      jobTemplate:
        spec:
          template:
            spec:
              containers:
              - name: hello
                image: busybox
                args:
                - /bin/sh
                - -c
                - date; echo Hello from the Kubernetes cluster
              restartPolicy: OnFailure
关键词 ： jobTemplate

CronJob 是一个 Job 对象的控制器（Controller）（正如同 Deployment 与 ReplicaSet 的关系一样）

CronJob创建和删除Job的依据，是schedule字段定义的


"*/1 * * * *"
    
    */1 中的 * 表示从 0 开始，/ 表示“每”，1 表示偏移量。所以，它的意思就是：从 0 开始，每 1 个时间单位执行一次

    时间单位：Cron 表达式中的五个部分分别代表：分钟、小时、日、月、星期。

如上：
每分钟执行一次，执行对象：jobTemplate定义的Job


由于定时任务的特殊性，很可能某个 Job 还没有执行完，另外一个新 Job 就产生了。这时候，你可以通过 spec.concurrencyPolicy 字段来定义具体的处理策略。比如：

1、concurrencyPolicy=Allow，这也是默认情况，这意味着这些 Job 可以同时存在；

2、concurrencyPolicy=Forbid，这意味着不会创建新的 Pod，该创建周期被跳过；

3、concurrencyPolicy=Replace，这意味着新产生的 Job 会替换旧的、没有执行完的 Job。


而如果某一次 Job 创建失败，这次创建就会被标记为“miss”。当在指定的时间窗口内，miss 的数目达到 100 时，那么 CronJob 会停止再创建这个 Job。

这个时间窗口，可以由 spec.startingDeadlineSeconds 字段指定。比如 startingDeadlineSeconds=200，意味着在过去 200 s 里，如果 miss 的数目达到了 100 次，那么这个 Job 就不会被创建执行了。



总结

    1、completions和parallelism字段的含义、Job Controller的执行原理
    2、Job 对象三种常见的使用方法
    3、Job 的控制器，叫作：CronJob

























