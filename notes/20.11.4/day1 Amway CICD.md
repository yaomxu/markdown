Amway CICD
Jenkins_job -> pipeline(Repository URL + Script Path) -> git_lab -> Jenkinsfile -> shared_pipeline_library -> groovy


Amway Newecommerce

CI: pipeline_ci_maven_root_pack_new_ecommerce.groovy

    Checkout code：Jenkins检出代码，获取分支名、commit等信息
    
    Compile code：使用mvn构建代码，命令：mvn -U clean compile -Dmaven.test.skip -s ./settings.xml，需要添加 settings.xml 到根目录
    
    Code quality check：使用mvn sonar插件做代码扫描，命令：mvn sonar:sonar -Dsonar.projectKey=new-ecommerce-amway-product-center -Dsonar.projectName=new-ecommerce-amway-product-center -s ./settings.xml
    
    Unit Test：使用mvn test测试代码，命令：mvn clean org.jacoco:jacoco-maven-plugin:prepare-agent install -Dmaven.test.failure.ignore=true -s ./settings.xml
    
    Test Coverage：使用Jenkins Jacoco插件统计行覆盖率，行覆盖率（Line Coverage）< 70% Pipeline状态 pipeline会Failed
    
    Package：使用mvn install打包代码，命令：mvn -U clean package -Dmaven.test.skip -s ./settings.xml
    
    Upload to Nexus：使用mvn deploy把其他依赖模块发布到Nexus上，命令：mvn deploy -Dmaven.test.skip
    
    Docker build： 打包 amway-product-center-boot 的jar为docker镜像，并上传至阿里容器仓库，用于CD发布流程
    
    Save Build Infomation： 保存CI构建信息、构建制品到DevOps Nexus上，用于CD发布流程

CD: pipeline_cd_edas_in_k8s.groovy
    
    Check Version And Env:  校验界面输入的 Version 和 Env
    
    Check User: 校验当前登录用户是否有发布对应环境的权限，发布人列表在CD Jenkinsfile 定义

    Check Artifact: 校验制品是否存在，获取CI构建信息

    Check Deploy Env: 如发布pd环境，需先成功发布ft1环境

    Deploy: 调用 Edas api 部署应用

    Save Deploy Info: 发布ft1环境成功，会保存该记录，用于发布pd环境时的校验

    Push Tag:  发布成功后，会 push 一个 Version 到gitlab仓库，用于记录

