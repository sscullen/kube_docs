******
Docker
******

Containers are the basic building block for machine independent cloud based computing. Kubernetes is a container orchestrator, allowing your application and its dependencies to be deployed independent of any given machine or architecture. Docker is the most common method for creating containers. We will go over the most useful methods for creating a Docker container for your application, which we will eventually be deploying to a Kubernetes cluster.

.. contents::

Dockerfile: Build Your Container Image
======================================

Dockerfiles are used to declaratively create images for Docker containers, which can be integrated into source control. This is a common theme among the dev ops topics we will be covering: finding ways to integrate configuration and deployment into the source control of your projects, so that they can be tracked and modified over time.

**Example Dockerfile**

.. code:: Dockerfile

    FROM registry.cullen.io/ubuntu-base:v0.0.8

    RUN apt update && apt install -y nginx

    ARG GITHUB_PAT

    COPY ./requirements.txt /code/requirements.txt

    WORKDIR /code

    RUN python3.7 -m pip install -r /code/requirements.txt

    RUN python3.7 -m pip install git+https://sscullen:$GITHUB_PAT@\
    github.com/sscullen/landsat_downloader.git@v0.0.4#egg=landsat_downloader
    RUN python3.7 -m pip install git+https://sscullen:$GITHUB_PAT@\
    github.com/sscullen/sentinel_downloader.git#egg=sentinel_downloader
    RUN python3.7 -m pip install git+https://sscullen:$GITHUB_PAT@\
    github.com/sscullen/spatial_ops.git@v0.0.2#egg=spatial_ops

    COPY . /code

    RUN cp -r /code/common/grid_files/ /usr/local/lib/python3.7/dist-packages/spatial_ops && \
        cp -r /code/common/data/ /usr/local/lib/python3.7/dist-packages/spatial_ops

    RUN python3.7 /code/manage.py collectstatic --no-input

    COPY nginx_site.txt /etc/nginx/sites-available/jobmanager

    RUN ln -s /etc/nginx/sites-available/jobmanager /etc/nginx/sites-enabled/jobmanager

    EXPOSE 80

    EXPOSE 443

    EXPOSE 5000

    CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--log-level=debug", "jobmanager.wsgi"]


**Dockerfile Keywords**

`FROM`
    Source image to use as a base. The foundation for your image. Often is images of popular linux distros but can also be images you have customized with other Dockerfiles, allowing for images with common requirements to be shared among many docker files. In the example above, `ubuntu-base` has Python3 and gdal already installed.

.. NOTE::
    Notice the URL for the docker image: this is how images are referenced and tagged for access from different docker registries, including the main docker hub. This is discussed more below in the :ref:`private registry<docker:Docker Private Registry>` section.

`RUN`
    Run a command inside the container. Each `RUN` command will add another "layer" (discrete change to the image that is tracked and transferred individually), and many layers will make the image large. `RUN` commands will often be chained with `&&` to reduce the image size.

.. NOTE::
    You can use the experimental `--squash` feature which reduces the amount of layers in an image regardless of how many `RUN` commands there are.

`ARG`
    Get environment variables from your machine into the image you are building. In the example this is used for Github authentication so no login or password prompts are needed. In the :ref:`build your image<docker:Build Your Image>` section we go over the different syntaxes for Linux and Windows for using your environment variables in the image build command.

`COPY`
    Move your source files and data from your local machine into the docker container image.

`WORKDIR`
    Set the `root` directory for the Dockerfile, where all the `RUN` commands will be executed and where the `COPY` commands will put the files they copy from your machine.

`EXPOSE`
    Expose the ports your application will be accessible on. For example, for an nginx docker image that is hosting web services, you will expose 443 and 80. For a Django application in development, you could use `django manage.py runserver 0.0.0.0:4000` to start your django instance, and in this case you would expose port 4000 to access your Django application.

`CMD`
    The command your docker container will run when it starts. For a simple Python webservice, your command would be starting the webserver application such as `nginx` or `gunicorn`. If you don't want your container to run a command here, you can use `['sleep', 'infinity']` so the container will wait for you to interact with it before shutting down. Once the `CMD` command finishes, the container shuts down.



Installing `pip` Packages Directly from Github
----------------------------------------------

In the example Dockerfile above, we have lines that look like this:

.. code:: Dockerfile
  
  RUN python3.7 -m pip install git+https://sscullen:$GITHUB_PAT@\
  github.com/sscullen/landsat_downloader.git@v0.0.4#egg=landsat_downloader

This allows us to install pip packages directly from Github. We can specify a specific branch and tag, allowing us to make sure we are using the right package. To avoid credential issues, we use a Github Personal Access token, which can be generated from the Github general settings page for your account. This is not required for a public repo.

To be a valid pip package, the repo should be structured like so:

.. code:: python

    repo_root/
        landsat_downloader # <-- actual python module source code
        .gitignore
        Pipfile # <-- requirements.txt equivalent for Pipenv virtual env manager
        Readme.md
        requirements.txt
        setup.py # <-- critical file for the pip package

The `setup.py` file is required, and contains metadata and package information. The version number in `setup.py` should match the latest release tag for your repo.

**Example setup.py**

.. code:: python

    from setuptools import setup

    setup(name='landsat_downloader',
        version='0.0.4',
        description='Utilities for downloading Landsat and Sentinel products from USGS',
        url='https://github.com/sscullen/landsat_downloader.git',
        author='Shaun Cullen',
        author_email='ss.cullen@uleth.ca',
        license='MIT',
        packages=['landsat_downloader'],
        zip_safe=False)

Pip will use `setup.py` to build the `.whl` package from your repo directly from your source code in the repo. This is important because it makes sure the version of the code we are using is up to date and correct. If we aren't doing active development on a project and only installing it as a dependency, then it is best to install in this way, rather than copying source code using a `COPY` command. If we are actively changing the code on our local machine, the `COPY` command makes more sense.

Exposing Your Service's Ports
-----------------------------

Using the `EXPOSE` directive is how you make your docker container service accessible to the outside world. This is also a critical concept in how Kubernetes exposes services from containers to the outside world. While it is possible to mount local volumes and interact directly inside your container, thus bypassing the "service" model employed by exposing ports for APIs and such, it is not a good idea to use Docker containers in this way. Even modest containers should have some sort of network service exposed for interacting with your application. 

Live interaction and intervention by a user in your container results in ephemeral changes to your container that are not maintained after the container restarts. In this vein, we should strive to make containers as "stateless" as possible, and move all data "persistence" requirements into dedicated data focused containers and services, which are designed with persistence in mind. More on this will be in the :ref:`Kubernetes section<kubernetes:Persistent Volumes and Claims>` on persistence. 


Build Your Image
================

Once you have your Dockerfile ready, you need to build the image. You do this by using the Docker CLI `build` command.

.. code:: bash
    
    docker build -f Dockerfile -t ubuntu_base:ver8 .

The above command specifies the Dockerfile with `-f` and the tag for the image with `-t`. Lastly, the `.` represents the directory to run the command in, so in that case it is your present working directory. A more complex build command where you passing command line args to be used by the `ARG` directive in your Dockerfile would look like this:

.. code:: bash
    
    docker build --build-arg GITHUB_PAT=${GITHUB_PAT} -f Dockerfile.django -t jobmanager-api:ver1 . --squash --no-cache

This command specifies the GITHUB_PAT `ARG` using BASH var substitution, on Windows with Powershell you would do `GITHUB_PAT=$env:GITHUB_PAT`. In either case, you are transferring env vars from your local machine into the container to be used during the build process. `--squash` collapses the layers of the docker image to keep the image small, and `--no-cache` will prevent the build process from using previous built layers. Caching will speed up the build process but it is sometimes nice to build the entire Dockerfile to make sure no issues have occurred since your last build.

.. WARNING::
    `--squash` is an experimental feature of Docker. To enable experimental features, edit the `/etc/docker/daemon.json` file and add `"experimental": true`. On Windows, edit the Docker Desktop settings, go to Docker Engine, and edit the json there.

If the build process completes successfully, you can list the current images on your machine with `docker images`.

.. code:: bash

    $ docker images
    REPOSITORY                              TAG                 IMAGE ID            CREATED             SIZE
    example                                 v0.0.1              e22f3bdb392b        9 hours ago         1.09GB

You can see the image id, tag, and size of the images. Image IDs are useful for having concrete references to your images.

Local Development Inside the Container
======================================

Once we have built the image, we want to work with it, test it locally, and make sure it is working properly. We run images with the `docker run` command:

.. code:: bash

    docker run -td -p 5001:5000 -e DEVELOPMENT=True -v /home/common/Development/job_manager/:/code -v /mnt/drobos/zeus/:/mnt/zeusdrobo zeus684440.agr.gc.ca/jobmanager-api:v0.0.9 bash

If the run command is successful, you will see a random string of characters. 

`-td` is telling Docker to run the image in a detached terminal, so that you can access it and disconnect from the container and it will stay running. 

`-p` defines port mapping from the container to your local machine, so for `-p 5001:5000`, 5000 is the container port, and 5001 is the local machine port. You can then access the service running on your docker container at `localhost:5001` on your machine. Remember that we `EXPOSE` port 5000 in the Dockerfile previously.

`-e` is for defining environment variables, here we are setting `DEVELOPMENT` to be `True`

`-v` is for mapping local directories on your machine to directories inside the container. Here we map the source code directory so we can make changes to the code on our machine and those changes will appear inside the container. We also mount another volume for data. Similar to the port mapping, the first entry before the `:` is the local machine, and the second entry is the container's directory.

The URL with the image tag is the full URL for the image. We will go over this in the :ref:`private registry section<docker:Docker Private Registry>` but just remember we don't need the registry URL in the image tag unless we are pushing and pulling from the registry.

Finally we have the command we want to run when we connect to the container, in this case we are running a `bash` shell to interact with the container, but in other more stripped down images you might only have access to the `sh` shell.

Accessing the Container
-----------------------

We can verify the container is running with the `docker ps` command:

.. code:: bash

    docker ps
    CONTAINER ID        IMAGE                    COMMAND             CREATED             STATUS              PORTS                                     NAMES
    c8075244d8a9        jobmanager-api:v0.0.24   "bash"              5 days ago          Up 5 days           80/tcp, 443/tcp, 0.0.0.0:5001->5000/tcp   sad_thompson

The container short name is `sad_thompson` in this example, it is randomly generated each time you run the container. Once you know the name of the container, you can access it with an `docker exec` command:

.. code:: bash

    docker exec -it sad_thompson bash

Here we are saying give me an interactive terminal for the container and run the command `bash`, this will leave us at a terminal inside the container. From there we can run commands for our application. `exit` will return us to our host machine.

When we are finished with the container, we can stop it from running with `docker kill sad_thompson`, and we can check if any containers are still running again by using the `docker ps` command.

Mounting Volumes Inside the Container
-------------------------------------

Mounting volumes inside the container is an important concept, useful for local development and getting data to and from the container, but also for Kubernetes, as that is the primary mechanism for getting configuration files into the the containers, in addition to adding persistence to the containers through volume mounts.

Once you are happy with the image created by the Dockerfile, and you have updated your code while developing inside the Docker container, and you are happy with those code changes, you will need to build your image one more time. After you do this build, you must tag the image with the full URL of the docker registry you want to use.

.. code:: bash

    docker images
    REPOSITORY                              TAG                 IMAGE ID            CREATED             SIZE
    example                                 v0.0.1              e22f3bdb392b        9 hours ago         1.09GB
    docker tag e22f3bdb392b registry.cullen.io/example_image:v0.0.1

The format for the image tag is <docker registry url>/<image name>:<semantic version tag>, the docker registry URL is used to differentiate which registry the image should be pushed to.

Once you have tagged the image, you push it with:

.. code:: bash

    docker push registry.cullen.io/example_image:v0.0.1

You'll also need to make sure that you login to the registry first using the command `docker login registry.cullen.io`.

.. NOTE::

    If you are setting up your own docker registry and it is not secured with HTTPS, you will need to add it as an insecure registry in the `/etc/docker/daemon.json` file by adding `"insecure-registries" : ["myregistrydomain.com:5000"]`, in a similar way that you enabled support for experimental features.


Docker Private Registry
=======================

If you have a lot of your own images and don't want to pay for an account on the Docker hub, you can set up your own registry. Digital Ocean has a `great tutorial <https://www.digitalocean.com/community/tutorials/how-to-set-up-a-private-docker-registry-on-ubuntu-18-04>`_, and you can also set up a docker `registry on your Kubernetes cluster <https://www.digitalocean.com/community/tutorials/how-to-set-up-a-private-docker-registry-on-top-of-digitalocean-spaces-and-use-it-with-digitalocean-kubernetes>`_ using Helm and an Ingress secured with a Let's Encrypt cert.

You pull images with the `docker pull <full image url>` command and push images with `docker push <full image url>` command.

The current private registry on the bare metal cluster is located at `registry.kub-eo.agr.gc.ca`.

Useful Docker Private Registry URL Endpoints
--------------------------------------------

`/v2/catalog`
    View available images.

`/v2/<image_name>/tags/list`
    View available tags for a given image.


Other Useful Docker CLI Commands
================================

`docker rmi <image_id>`
    Remove an image.


.. .. sidebar:: Optional Sidebar Title

..    Subsequent indented lines comprise
..    the body of the sidebar, and are
..    interpreted as body elements.

.. term 1
..     Definition 1.

.. term 2
..     Definition 2, paragraph 1.

..     Definition 2, paragraph 2.

.. term 3 : classifier
..     Definition 3.

.. term 4 : classifier one : classifier two
..     Definition 4.

.. Watch out for this:
..     | asdasdfasdf
..       asdasd
..     | aasdflkjasldfkj

.. But also this
..     | what the what
..     | what what

.. This is an ordinary paragraph, introducing a block quote.

..     "It is my business to know things.  That is my trade."

..     -- Sherlock Holmes

.. .. code:: python

..   def my_function():
..       "just a test"
..       print 8/2