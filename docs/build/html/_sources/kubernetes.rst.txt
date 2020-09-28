**********
Kubernetes
**********

Kubernetes is a container orchestration tool for deploying containers across many different physical machines organized into a cluster. We will cover only the very basics of getting a container you created up and running on Kubernetes. It is assumed that a cluster is already set up and can be accessed with the `kubectl` utility from your local machine. The official `Kubernetes documentation <https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/>`_ has good tutorials for setting up a cluster using `kubeadm`, and for local development and learning `Minikube <https://kubernetes.io/docs/setup/learning-environment/minikube/>`_ is easy to set up and get going with. It is assumed that the cluster is already set up or a managed Kubernetes service is available to you such as EKS or AKS.

.. contents::

YAML Manifests
==============

Resources on Kubernetes are defined by `.yaml` format manifest files. Manifest files can be applied to the cluster using `kubectl`, the Kubernetes command line interface, using `kubectl apply -f manifest.yaml`. For each resource type below an example `.yaml` file will be provided.

Pods and Containers
===================

Pods are the smallest building block of Kubernetes that can be queried directly. The can contain one or more containers, and the containers can expose ports in order to be accessed individually from the overall pod. Volumes can be mounted and assigned to individual containers. Pods have labels which allow services to direct traffic to specific containers within a pod. Think of a pod as a grouping of containers. Different pods can communicate with each other in different ways, including a shared message queue such as Rabbit MQ. In this way, related containers do not have to be in the same pod. In fact, it is common for pods to have only a single container. 

Example Pod YAML
----------------

.. code:: yaml

    apiVersion: v1
    kind: Pod
    metadata:
    name: ubuntu-worker 
    labels:
        name: ubuntu-worker
    spec:
    containers:
        - name: ubuntu-worker-container
        image: registry.kub-eo.agr.gc.ca/ubuntu-base:v0.0.8 
        ports:
            - name: web
            containerPort: 80
        volumeMounts:
            - name: nfsvol 
            mountPath: /mnt/zeusdrobo
        command:
            - "sleep"
        args: 
            - "infinity"
    imagePullSecrets:
        - name: regcred
    volumes:
        - name: nfsvol
        persistentVolumeClaim:
            claimName: nfs-pvc-miniostorage

Pod Definition Key Aspects
--------------------------

name
    Used for querying the status of the pod.

labels
    Used to identify the pod so that services can correctly send traffic to the right pod. In the service definition `selectors` are used to match the `labels` defined for the pod.

containers:image
    Specifies the image for the container.

containers:ports
    Specifies the ports exposed by the container, and therefore the pod.

containers:volumeMounts
    Specifies which of the volumes defined for the pod will be mounted in this container and to which path.

containers:command and args
    The command the container will run on start up with which variables.

imagePullSecrets
    The credentials for your private registry so that Kubernetes is able to pull the image. This requires some extra steps to set up which will be covered in the :ref:`secret section<kubernetes:Secrets>`.

volumes
    The persistent volume claim that allows the pod to take a share of a persistent volume and provide that persistence to its containers as a mount point.

Common Commands for Pods
------------------------

View all pods for the default namespace:

.. code:: bash

    kubectl get pods

View pods for a specific namespace:

.. code:: bash

    kubectl get pods --namespace namespace_name

View pods for all namespaces:

.. code:: bash
    
    kubectl get pods -A

View details for a pod:

.. code:: bash

    kubectl describe pod pod_name

.. code:: bash

    kubectl get pod pod_name -o yaml

View logs for a pod with one container:

.. code:: bash

    kubectl logs pod_name

View logs for a pod with many containers:

.. code:: bash

    kubectl logs pod_name -c container_name

Interact inside a container:

.. code:: bash

    kubectl exec -it pod_name -- bash

Similarly to logs, if you have a pod with more then one container, use `-c` to specify the container.

Delete a pod:

.. code:: bash

    kubectl delete pod pod_name

When you delete a pod, it doesn't get recreated automatically; that is where a :ref:`deployment<kubernetes:Deployments>` comes in handy. Often to re-apply a new configuration or if there are problems with a pod, you will need to delete it and re-apply the manifest to recreate the pod.

Pods are where your code runs, and services are how your code communicates inside the cluster and out.

Services
========

Services provide an interface to communicate with the applications running in your pods. The two major types of services are `ClusterIP` and `NodePort`. ClusterIPs are used for inter-cluster communication, while NodePorts enable communication from outside the cluster. For pod to pod communication it is common to use ClusterIP services to do this. NodePorts require access to the IP or hostname of the nodes (the physical hardware providing the resources required by your pods) running your cluster, and the service is differentiated by the port number. A nicer way of allowing access from outside your cluster is with subdomains through an Ingress and ingress manager like a load balancer. That will be covered in the :ref:`ingress section<kubernetes:Ingress>`.

So if you want to access a pod running a service on port 6379, and one of your node's IP address is 10.117.206.94, you would create a `NodePort` service that has a nodePort of 30637, and selectors that are equivalent to the pod's labels. The result is that your pod's service is accessible outside the cluster at `10.117.206.94:30637`. If your node had a hostname assigned to it, you could also use that, so it would be `node_hostname.local:30637`.

If you don't specify your nodePort, one will be automatically assigned in the range of port numbers between 30000-32000. Keep this range in mind when manually specifying node ports. Ports in this range will not conflict with the default ports in use on your node.

ClusterIP services don't have a nodePort and are not accessible by machines outside the cluster.

Example Service YAML
--------------------

.. code:: yaml

    apiVersion: v1
    kind: Service
    metadata:
    name: redis-service
    labels:
        name: redis-service
    spec:
    type: NodePort
    ports:
        - port: 6379
        nodePort: 30637
        targetPort: 6379
    selector:
        app: redis
        release: redis-dev
        role: master

Service Definition Key Aspects
------------------------------

`type`
    Can be `NodePort` or `ClusterIP`.

`ports`
    Defines the port that the service will send traffic to on the pod (port and targetPort), while for `NodePort` the nodePort defines what port on your node that requests will be coming from.

`selector`
    Corresponds to the `labels` defined on the pod you are wanting to send traffic to. For example, if you pod has a label `name: ubuntu-worker`, then your selector will have `name: ubuntu-worker` as well.

Commands for Services
---------------------

See the :ref:`common commands for Pods section<kubernetes:Common Commands for Pods>` for examples on how to fetch services using `kubectl get` and `kubectl describe` with the resource type `svc`.

For example:

.. code:: bash

    kubectl get svc

The above will show all the services for the default namespace.

Deleting services works the same as pods as well.

Ingress
=======

Ingress is a special kind of service that differentiates the destination of the traffic based on the domain the request came from. This requires a load balancer which will be a assigned an IP address that is accessible outside the cluster. This load balancer IP can be assigned an A record (a primary DNS entry that points to machine IPs), such as `ingress.kub-eo.agr.gc.ca`. Once that `A record` is in place, `CNAME records` (alias DNS records that point domain names to `A record`s) can be created that point to `ingress.kub-eo.agr.gc.ca`. So `subdomain.testing.kub-eo.agr.gc.ca` will point to `ingress.kub-eo.agr.gc.ca`. When a request to `subdomain.testing.kub-eo.agr.gc.ca` is received, the load balancer can see which domain the request was for, and will forward it to the correct pod based on that instead of the port like NodePort services. This is the primary way that web services are built because using domains and subdomains instead of port numbers is much more user friendly.

The caveat to using ingress services is that a load balancer must be available. Cloud based providers have their own load balancers for you to use. If you are running your own bare metal cluster, you must use something like `metal lb <https://metallb.universe.tf/>`_ which provides a load balancer implementation for you to use. 

Example Ingress YAML
--------------------

.. code:: yaml

    apiVersion: networking.k8s.io/v1
    kind: Ingress
    metadata:
    name: jobmanager-ingress
    annotations:
        nginx.ingress.kubernetes.io/proxy-body-size: "4000m"
        nginx.ingress.kubernetes.io/proxy-send-timeout: "600"
        nginx.ingress.kubernetes.io/proxy-read-timeout: "600"
        kubernetes.io/ingress.class: nginx
    spec:
    rules:
    - host: s2d2.kub-eo.agr.gc.ca
        http:
        paths:
        - backend:
            serviceName: jobmanager-api
            servicePort: 8080

Ingress Definition Key Aspects
------------------------------

`annotations`
    Most load balancers use nginx as a reverse proxy, therefore there are some nginx settings that we can change for our ingress. If our ingress is sending big files back and forth, we can up the `proxy-body-size` to 4 GB, and increase the timeouts to 5 minutes if transfers take a long time.

`rules`
    Here we set the domain that the ingress relates to, where the request should be sent to. In this case we are using a ClusterIP service that is listening on port 8080. 

Ingress Commands
----------------

You use similar commands to pods and services with ingresses, only with the `ingress` resource type:

.. code:: bash

    kubectl get ingress

Deployments
===========

Deployments are a way of bundling together manifests for pods, services, persistent volume claims, and more, into a single `yaml` manifest. In addition, the deployment will automatically restart deleted pods, which makes it ideal for applications where the configuration changes a lot. Deployments get auto-generated names, so you will see deployments with names like `deployment-name-adsfas-asdfas` with the last 2 suffixes being auto generated IDs for the deployment resource. In most cases, deployments with pods and services should be used instead of pod and service yamls individually. 

In the :ref:`Helm and Helm Chart section <kubernetes:Helm: Standardized Deployment Format>` we go over the use of Helm to manage deployments, but it brings even more power such as variable templating, subcharts, and release versioning and rollbacks. Think of Helm and helm charts as deployments on steroids. You don't always need Helm, but you almost always should be using a deployment.

Example Deployment YAML
-----------------------

.. code:: yaml

    apiVersion: apps/v1
    kind: Deployment
    metadata:
    name: jobmanager-api
    spec:
    selector:
        matchLabels:
        app: jobmanager-api
    replicas: 1
    template:
        metadata:
        labels:
            app: jobmanager-api
        spec:
        containers:
            - name: jobmanager-api
            image: registry.cullen.io/jobmanager-api:v0.0.24
            command: ["gunicorn"]
            args:
                [
                "--bind",
                "0.0.0.0:5000",
                "--log-level=debug",
                "jobmanager.wsgi",
                "--timeout",
                "300",
                ]
            ports:
                - containerPort: 5000
                protocol: TCP
            imagePullPolicy: Always
            volumeMounts:
                - name: nfs-media-vol
                mountPath: /code/media
                - mountPath: /code/config.yaml
                subPath: config.yaml
                name: jobmanager-config-volume
            - name: jobmanager-api-nginx
            image: registry.cullen.io/jobmanager-api:v0.0.24
            command: ["nginx"]
            args: ["-g", "daemon off;"]
            ports:
                - containerPort: 80
                protocol: TCP
                - containerPort: 443
                protocol: TCP
            imagePullPolicy: Always
            volumeMounts:
                - name: nfs-media-vol
                mountPath: /code/media
                - mountPath: /code/config.yaml
                subPath: config.yaml
                name: jobmanager-config-volume
                - mountPath: /etc/nginx/sites-available/jobmanager
                subPath: jobmanager
                name: jobmanager-api-nginx-siteconf
                - mountPath: /etc/nginx/nginx.conf
                subPath: nginx.conf
                name: jobmanager-api-nginx-conf
        imagePullSecrets:
            - name: regcred
        volumes:
            - name: nfs-media-vol
            persistentVolumeClaim:
                claimName: nfs-media-data
            - configMap:
                name: jobmanager-config
                items:
                - key: config.yaml
                    path: config.yaml
            name: jobmanager-config-volume
            - configMap:
                name: jobmanager-api-nginx-siteconf
                items:
                - key: jobmanager
                    path: jobmanager
            name: jobmanager-api-nginx-siteconf
            - configMap:
                name: jobmanager-api-nginx-conf
                items:
                - key: nginx.conf
                    path: nginx.conf
            name: jobmanager-api-nginx-conf

It may seem like there is a lot going on, but keep in mind that there is a lot of overlap with the previously covered resources we have seen before, pods and services.

Manifests can be bundled together in one file, seperated by `---`. In this way we can include a service that the deployment will use at the top of the deployment manifest.

.. code::

    apiVersion: v1
    kind: Service
    metadata:
    name: jobmanager-api
    spec:
    ports:
    - port: 5000
        protocol: TCP
        name: gunicorn
    - port: 8080
        protocol: TCP
        name: static
    selector:
        app: jobmanager-api
    ---
    apiVersion: apps/v1
    kind: Deployment
    metadata:
    name: jobmanager-api
    spec:
    selector:
        matchLabels:
        app: jobmanager-api
    replicas: 1
    template:
        metadata:
        labels:
            app: jobmanager-api
    ...

Deployment Commands
-------------------

You use similar commands to pods and services with deployments, only with the `deployment` resource type:

.. code:: bash

    kubectl get deployment

Configmaps
==========

Configmaps are the resource to get configuration into your pods and deployments. Any configuration files or environment variables can be set with configmaps. You can set environment variables in a pod definition, but the recommended way to get credentials and config files into your pods is to use configmaps, as it will let you save whole files of config as yaml or json and have that yaml or json be mounted inside your container in a similar way to how data volume mounts work. That is why configmaps are accessed and added to to a pod in the same way that volume mounts from persistent volume claims are.

In the above :ref:`example deployment YAML<kubernetes:Example Deployment YAML>` there are configmaps being loaded and mounted as files inside the pods under the `volumes` section. In this section we will go over how to create configmaps from config files, and more importantly how to update the configmap from a changed config file as your configurations change.

Regular volume mounts using a persistent volume claim name and a config map created using a `.yaml` config file:

.. code:: yaml
    
    template:
        ...
        container:
        ...
        volumeMounts:
            - name: nfs-media-vol
            mountPath: /code/media
            - mountPath: /code/config.yaml # Path to mount the configmap
            subPath: config.yaml # Specified so the configmap file mount doesn't replace the whole volume
            name: jobmanager-config-volume
    volumes:
        - name: nfs-media-vol
        persistentVolumeClaim:
            claimName: nfs-media-data
        - configMap:
            name: jobmanager-config
            items:
            - key: config.yaml # <-- key that points to the YAML file
                path: config.yaml # <-- name of the YAML file when it is created in the pod

Example Creating A Configmap
----------------------------

Assume you have a configuration file named `config.yaml` that looks like this:

.. code:: yaml

    S3_URL: http://s3.kub-eo.agr.gc.ca
    S3_ACCESS_KEY: <s3 access key here>
    S3_SECRET_KEY: <s3 secret key here>
    S3_REGION: us-east-1
    PSQL_DB: jobmanagerapp
    PSQL_DB_USER: jobmanagerapp
    PSQL_DB_PASS: <db password here>
    PSQL_DB_URL: "10.96.107.240"
    PSQL_DB_PORT: "5432"
    USGS_EE_USER: <username here>
    USGS_EE_PASS: <password here>
    ESA_SCIHUB_USER: <username here>
    ESA_SCIHUB_PASS: <password here>
    DJANGO_SETTINGS_MODULE: jobmanager.settings
    RABBIT_MQ_USER: user
    RABBIT_MQ_PASS: <rabbit password here>
    RABBIT_MQ_URL: "10.96.181.64"
    RABBIT_MQ_PORT: "5672"
    DJANGO_SECRET: <django secret here>
    REDIS_PASS: <redis password here>
    REDIS_PORT: "6379"
    REDIS_HOST: "10.96.12.117"
    MAILGUN_API_URL: https://api.mailgun.net/v3/mg.satdat.space/messages
    MAILGUN_API_KEY: <api key here>

To create a config map from this file, you would use this command:

.. code:: bash

    kubectl create configmap jobmanager-config --from-file config.yaml

If you have several versions of your config, but inside the pod the config needs a standardized name, you can rename the config for access inside the pod.

.. code:: bash

    kubectl create configmap jobmanager-config --from-file=config.yaml= config_with_nonstandardname.yaml

So the config_with_nonstandardname.yaml will be renamed to config.yaml inside the pod. In this way, all of your config files do not have to be named the same.

To view your configmaps:

.. code:: bash

    kubectl get configmaps

    kubectl get configmap jobmanager-config -o yaml

The above command will let you see the structure of the files and values that make up your configmap. In the above case, the key `config.yaml` will be assigned to a valid YAML serialized string, so that when the configmap is mounted, that key will be used to recreate the file and make it accessible inside the pod. Other keys and values can be stored inside a configmap. 

To update your configmap:

.. code:: bash

    kubectl create configmap jobmanager-config --from-file config.yaml -o yaml --dry-run | kubectl replace -f -

After you update your configmap, its a good idea to restart your pods with `kubectl delete pod <pod_name>`.

.. WARNING::
    If you are not using a deployment, your pod will not be recreated automatically, so don't forget to recreate the pod with `kubectl apply -f pod_manifest.yaml`

If you have user credentials that are common to many pods, it might be better to use a :ref:`secret<kubernetes:Secrets>`, similar to how we use a secret for the docker private registry credentials in order to pull docker images. But keep in mind, secrets provide no security beyond configmaps by default. It is just another resource type for credentials that are common across your cluster. Don't assume secrets are secret.

Secrets
=======

Secrets are base64 encoded configuration and credential storage. Most useful for common config across many pods, or to standardize how you store credentials in your cluster.

An example of creating a secret is the docker private registry secret, where the docker login credentials stored in a .json file are saved in a secret and used by pods to pull the docker image they need.

.. code:: bash

    kubectl create secret generic do-registry \
  --from-file=.dockerconfigjson=docker-config.json \
  --type=kubernetes.io/dockerconfigjson

Secrets are very similar to configmaps, except they are base64 encoded. So to get a secret you would retrieve the secret as a yaml:

.. code:: bash

    kubectl get secret secret-name -o yaml

    apiVersion: v1
    data:
    redis-password: Q2p3QlR6cmg5Wg== # base64 encoded credential we are looking for
    kind: Secret
    metadata:
    ...

To view the credential, we need to decode it like so:

.. code:: bash

    echo Q2p3QlR6cmg5Wg== | base64 --decode

    CjwBTzrh9Z

Persistent Volumes and Claims
=============================

Persistent volumes allow you to you store data across pod restarts, and share data among pods in the case of NFS shares. Persistent volumes are the general storage resource, and persistent volume claims are specific claims to chunks of those persistent volumes which are dedicated to specific pods. 

In addition to manually specified persistent volumes and persistent volume claims, there are storage classes which enable auto provisioning. This means that when a pod requests a certain amount of storage from a storage class that supports provisioning, the provisioner automatically creates the claim and allows the pod to access it. You don't have to create the PV and PVC, they are created for you by the provisioner when you create the pod.

Example Persistent Volume and Claim YAML
----------------------------------------

Persistent volume:

.. code:: yaml

    apiVersion: v1
    kind: PersistentVolume
    metadata:
    name: nfs-pv-miniostorage
    spec:
    capacity:
        storage: 10Ti
    accessModes:
        - ReadWriteMany 
    persistentVolumeReclaimPolicy: Retain 
    nfs: 
        path: /mnt/md0/minio_storage 
        server: 10.117.206.94
        readOnly: false


Persistent volume claim:

.. code:: yaml

    apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
    name: nfs-pvc-miniostorage 
    spec:
    accessModes:
    - ReadWriteMany      
    resources:
        requests:
        storage: 10Ti

The persistent volume references a specific type of storage, whether that is block storage provided by a cloud provider, an nfs share specified by export and IP address of the server, or others. It is the actual storage that persistence volume claims can try to access and provide to the pods that have references to those claims.

The persistent volume claim sets the requirements, and then Kubernetes tries to find a matching persistent volume that can meet those requirements. Usually if you only have one persistent volume and claim being created at a time, the correct persistent volume will be matched to your persistent volume claim, if it is able to meet the requirements of the persistent volume claim. If you want to explicitly match PV and PVC, you can use a `claimRef` in the PV and `volumeName` in the PVC.

NFS
---

NFS shares as persistent volumes allows ReadWriteMany data access, which allows multiple pods to read and write from the same volume at the same time. If we create an NFS server outside of the cluster, we can access the data in the persistent volume as a normal network share. The trade off is that auto provisioning is not possible.

NFS shares can be mounted ephemerally directly in the pod manifest, or through persistent volumes and claims, which are then referenced in the pod manifest. The primary difference is you should use persistent volumes if you want the NFS share to managed by Kubernetes and documented in your source control. This should be used if the shares are used across many different pods, as you would only have to change persistent volume or claim once, instead of all of the pods where the NFS settings are defined.

See this `article <https://cloud.netapp.com/blog/kubernetes-nfs-two-quick-tutorials-cvo-blg>`_ for more info on NFS and the different ways to access the network shares in your pods.

Auto Provisioning
-----------------

Auto provisioning is when a persistent volume claim is specified with a storage class that with a supporting provisioner. When the claim is specified, the corresponding volume is created automatically. There is an `NFS provisioner helm chart <https://github.com/helm/charts/tree/master/stable/nfs-server-provisioner>`_, which will create NFS persistence volumes automatically. The trade off is that these NFS volumes are not accessible outside the cluster, and mounting them as regular network shares is not possible (or at least not easy). 

On bare metal clusters, where block device volume storage from cloud providers is not available, dynamic provisioning is possible through the use of `OpenEBS <https://openebs.io/>`_. A `cstor storage pool <https://docs.openebs.io/docs/next/cstor.html>`_ of block devices can be created using block devices on each node, which creates a pool of storage that you can use to create persistent volumes from. After you create the pool and name the storage class, you can use that storage class in helm charts and deployments to create the persistent volume from the storage pool automatically.


Helm: Standardized Deployment Format
====================================

Helm is a tool that allows you to deploy a set of resources to Kubernetes in a standardized and customizable way. You can bundle complex configurations, dependencies in a format called a helm chart that can be transferred and customized through templating that allows users to install your application with minimal effort. In addition, helm will track the version of the application, allowing for easy rollbacks if things go wrong. Helm charts can be simple or very complex, but in any case it is a good idea to become comforatable with Helm and Helm charts, as you will often be using them to install 3rd party dependencies for your application, such as Postgres, RabbitMQ, Redis, Minio, and others.

Follow the directions in the `official Helm docs <https://helm.sh/docs/intro/quickstart/>`_ to install Helm and begin using it.

Example of Using Helm
---------------------

Here we are going to use Helm to install Postgres on our cluster.

First we find the postgres helm chart we want to use. In this case we will be using the `bitnami helm chart <https://github.com/bitnami/charts/tree/master/bitnami/postgresql>`_. 

Then we make sure we have the bitnami repo added to helm:

.. code:: bash

    helm repo add bitnami https://charts.bitnami.com/bitnami

    helm repo update

Then we install postgres, setting the release name to `psql`, using all the default settings:

.. code:: bash

    helm install psql bitnami/postgresql

More likely, we would want to change a few settings, so we would use the `--set` arg to change some configuration settings:

.. code:: bash

    helm install psql bitnami/postgresql --set persistence.storageClass=openebs-hdd-storageclass,persistence.size=100Gi,postgresqlPassword=sBwqls0FpQ

You can view all the available configuration options on the `chart repo ReadMe <https://github.com/bitnami/charts/tree/master/bitnami/postgresql#parameters>`_.


To see the current helm installs:

.. code:: bash

    helm list

To remove a helm install:

.. code:: bash

    helm uninstall psql

Helm Charts
-----------

If you have a complex application, you can make it easier to install for you and others by creating a helm chart to bundle it together.

The general format of a helm chart has this structure:

.. code:: python

    root/
        .helmignore
        Chart.yaml
        values.yaml
        templates/
        charts/
        configfiles/

The `templates` directory contains your yaml manifests for the different resources for your application. Inside the yaml files you can add templating directives that pulls values from the `values.yaml` file. 

.. code::

    apiVersion: v1
    kind: PersistentVolume
    metadata:
    name: nfs-pv-{{ include "jobmanager-api.fullname" . }} # templating directive
    spec:
    capacity:
        storage: 14Ti
    accessModes:
        - ReadWriteMany 
    persistentVolumeReclaimPolicy: Retain 
    nfs: 
        path: /mnt/drobo 
        server: zeus684440.agr.gc.ca
        readOnly: false

The  `values.yaml` file is where you setup your default values for your helm chart, and these are also the values that can be overridden by the user with the `--set` args when installing the helm chart.

`Chart.yaml` contains general info about your chart, such as version, dependencies, and other packaging info.

The `charts/` directory is where you would put subcharts that your chart depends on. Subcharts are full helm charts that your main chart requires to function. So here you could add subcharts for postgres and rabbitmq if your application required those applications to function. Subcharts, and full charts, can be stored as compressed tar archives.

A helm "repo" is a simple web accessible directory with helm charts stored as compressed tar archives with the correct naming convention (`postgresql-8.2.1.tgz`) and an `index.yaml` file that summarizes the available helm charts in the repo.