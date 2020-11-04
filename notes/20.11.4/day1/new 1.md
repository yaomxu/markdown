kubectl command

main obj：Pod

命令名			类型				作用
get				查			列出某个类型的下属资源           	
describe		查			查看某个资源的详细信息
logs			查			查看某个 pod 的日志
create			增				   新建资源
explain			查			查看某个资源的配置项
delete			删			 删除某个资源
edit			改			修改某个资源的配置项
apply			改			应用某个资源的配置项

具体--help查

get :   kubectl get <资源名>     
	-n  指定namespace
	-o , --output=   json|yaml|wide|name|custom-columns=...|custom-columns-file=...|go-template=...|go-template-file=...|jsonpath=...
	-f , --filename=  filename,directory,URL
	
describe:	kubectl describe  <资源名>  <实例名> 
	-n	指定namespace
	
	kubectl describe pod pod_name -n namespace
	
	基础属性：Node、labels和Controlled By。通过Node你可以快速定位到 pod 所处的机器，从而检查该机器是否出现问题宕机等。
			通过labels你可以检索到该 pod 的大致用途及定位。而通过Controlled By，你可以知道该 pod 是由那种 k8s 资源创建的，
			然后就可以使用kubectl get <资源名>来继续查找问题。
			
	内部镜像信息：Image 	
	
	事件：Event。没有任何Events的话，就说明该 pod 一切正常。当 pod 的状态不是Running时，这里一定会有或多或少的问题
		
create:		kubectl create -f <配置文件名.yaml>
			kubectl create <资源类型> <资源名>     service、namespace、deployment等
			
explain:	kubectl explain <配置名>      kubectl explain pod.matedata

delete:		kubectl delete <资源类型> <资源名>

edit:		kubectl edit <资源类型> <资源名>	 kubectl edit pod pod_name

apply:		kubectl apply -f <新配置文件名.yaml>		``kubectl apply -f  URL.yaml
	
	
	
	
	
	
	
	
	
	