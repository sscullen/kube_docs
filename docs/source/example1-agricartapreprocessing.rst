********************************************
Example 1 - Simple - Agricarta Preprocessing
********************************************

.. contents::

Summary
=======

The first example is as simple as you can get for running an application on Kubernetes. We will have :ref:`one pod with one container <kubernetes:Pods and Containers>`, :ref:`one service <kubernetes:Services>`, :ref:`one configmap <kubernetes:Configmaps>`, with a simple Flask web server wrapper around the application. Data will be stored on NFS :ref:`persistent volumes <kubernetes:Persistent Volumes and Claims>` with a simple file to indicate processing status. Our input data is already stored on an NFS share, so we can mount that inside our pod. For future improvements, you could look to storing the data as S3 objects to make deployment to the cloud easier, in addition to leveraging GDAL's ability to load from S3 data sources to make incremental networked file loads possible.

Architecture
============

.. mermaid::

    graph TD
        A[POST request]-. /agricarta/preprocessing .->B[Ingress service]
        B -. job id .-> A
        B <--> F
        D[NFS Persistent Volume] --> F
        E[Configmap] --> F
    
    subgraph Pod
        F[Flask Web Server] --> G[Agricarta]
    end

Prerequisites
=============

Imagery data stored on an NFS network share that is accessible to our cluster. For this example we are going to create 2 NFS exports that will be used to store the data inputs and outputs. On the NFS server, you will need to create the directory, edit the /etc/exports file, and restart the nfs-kernel-server. There will also be datasets required for processing that we will mount from a NFS share. All of these shares will be mounted using persistent volume claims inside the container.

You can verify the new mounts are accessible by running `showmount -e <NFS server IP>` from the cluster node machines.

Build the Container
===================

Here's the Dockerfile we will use:

.. code:: Dockerfile

    FROM ubuntu:18.04

    COPY ./requirements.txt /code/requirements.txt

    WORKDIR /code

    RUN apt update

    RUN apt install -y software-properties-common build-essential

    RUN apt-add-repository -y ppa:deadsnakes/ppa

    RUN apt update

    RUN apt install -y python3.7 python3.7-dev python3.7-venv python3-pip zlib1g zlib1g-dev libpng-dev libjpeg-dev

    RUN python3.7 -m pip install --upgrade pip
    RUN python3.7 -m pip install numpy
    RUN apt install -y gdal-bin gdal-data libgdal-dev

    RUN python3.7 -m pip install gdal==`gdal-config --version` --global-option=build_ext --global-option="-I/usr/include/gdal/"

    RUN python3.7 -m pip install -r /code/requirements.txt

    COPY . /code

    EXPOSE 5000

    #CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--log-level=debug", "jobmanager.wsgi"]


Service
=======

For the service we will use a Nodeport, but if we had easy access to creating DNS entries, an Ingress would be preferable.

.. code:: yaml

    apiVersion: v1
    kind: Service
    metadata:
    name: agricarta-nodeport
    spec:
    selector:
        app: agricarta
    ports:
        - protocol: "TCP"
        port: 5000
        targetPort: 5000
        nodePort: 30199
    type: NodePort

Deployment
==========

The important parts of the deployment are the single container, which starts our Flask server, and the volume mounts, one for the NFS that our imagery is mounted on, and one for the configmap that stores our generic config options.

.. code:: yaml

    apiVersion: apps/v1
    kind: Deployment
    metadata:
    name: agricarta
    spec:
    selector:
        matchLabels:
        app: agricarta
    replicas: 1
    template:
        metadata:
        labels:
            app: agricarta
        spec:
        containers:
            - name: agricarta
            image: registry.kub-eo.agr.gc.ca/agricarta:v0.0.2
            env:
            - name: FLASK_APP
                value: server.py
            - name: FLASK_DEBUG
                value: "1"
            command: ["flask"] # env FLASK_APP=server.py FLASK_DEBUG=1 flask run --host 0.0.0.0
            args:
                [
                "run",
                "--host",
                "0.0.0.0"
                ]
            ports:
                - containerPort: 5000
                protocol: TCP
            imagePullPolicy: Always
            volumeMounts:
                - name: nfs-miniostorage-volume
                mountPath: /code/miniostorage
                - mountPath: /code/config.yaml
                subPath: config.yaml
                name: agricarta-preprocessing-config-volume
        imagePullSecrets:
            - name: regcred
        volumes:
            - name: nfs-miniostorage-volume
            persistentVolumeClaim:
                claimName: nfs-pvc-miniostorage
            - configMap:
                name: agricarta-preprocessing-config
                items:
                - key: config.yaml
                    path: config.yaml
            name: agricarta-preprocessing-config-volume

Configmaps
==========

For the configmap, we are using a config.yaml file for the generic options, and the specific job options will be set by a JSON object in the POST request for our API.

.. code:: yaml

    ROOT_DIR: /code
    # WORKING_DIR: /code/workingdir
    DEPENDENCIES_DIR: /code/miniostorage/required_datasets
    SRTM_DIR: /code/miniostorage/required_datasets/dem/SRTM41
    IMAGERY_STORAGE: /code/miniostorage
    # RESOLUTION: 10
    # CPU_CORES: 6
    # LOGGING_DIR: /code/logs
    LOGGING_CONFIG:
    console_level: DEBUG
    file_level: DEBUG
    # DELETE_INTERMEDIATE: True
    
    # Projection as PROJ4 string as string
    PROJECTION: "+proj=aea +lat_1=44.75 +lat_2=55.75 +lat_0=40 +lon_0=-96 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs"
        
    # Imagery System Parameters
    # NOTE: Custom parameters can be defined. Bellow is an example of the defaults
    # System will use defaults if 'params' NOT defined within this file
    #      LC8 'products' --> dn = Digital Number
    #                         radiance = Spectral Radiance
    #                         sr = Surface Reflectance
    #                         toa = Top of Atmosphere Reflectance
    #      RCM / RS2 'filter' --> gamma = Gamma Filter
    #      RCM / RS2 'modes'  --> W2 = Wide Beam #2
    #      RCM / RS2 'units'  --> amp = Amplitude
    #                             dB = Decibel
    #                             pow = Power
    PARAMS: 
    LC8:
        bands:
        - B2
        - B3
        - B4
        - B5
        - B6
        - B7
        product: sr
        resamp_clip: True
    RCM:
        bands:
        - CH
        - CV
        - HH
        - HV
        - VH
        - VV
    RS2:
        filter: gamma
        modes:
        - W2
    S2:
        bands:
        - B02
        - B03
        - B04
        - B05
        - B8A
        - B11
        - B12
        resamp_clip: True


The command we use to create the configmap from the config.yaml file is:

.. code:: bash

    kubectl create configmap agricarta-preprocessing-config --from-file config.yaml

Persistent Volume and Claim
===========================

The persistent volume is a NFS share that we have access to inside the cluster and out, so we can mount it as a regular network share in addition to using it as a persistent volume.

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

API
===

The Nodeport service means our API is accessible on port 30199 on the node hostnames and IP addresses. The end point is /agricarta/preprocessing, it supports the POST HTTP method, and the processing parameters are JSON data that you include with the post request.

.. code:: JSON

    {

        "imagery_list": ["LC08_L1TP_015028_20200814_20200822_01_T1", "LC08_L1TP_015029_20200814_20200822_01_T1"],

        "resolution": 10,

        "cores": 2,

        "delete_intermediate": false

    }

We can use Postman to test our API.

Data Management and Access
==========================

Because we have access to the NFS share with the imagery we are using, we can use the NFS share to host the preprocessing results. Thus the results are acessible on the NFS share and the S3 Minio instance that NFS share is also backing.