# The Apache Software Foundation - Logging Website

This is the source code for the website at [logging.apache.org](https://logging.apache.org).

## Develop this website

To develop content for this website, you need to make sure you have
Docker installed. Once installed, you can run this command
to create a docker image:

```
$> cd <your project folder>
$> docker build -t apache/logging_site .
```

or run: ```./run-docker-build.sh```

Whenever you change something in the Docker's dependencies, you have to recreate the Docker image.
Afterwards, you can run the website.

To run the website in serve mode (running a server to quickly check your code)
you'll have to run this command:

```
docker run --rm -p 4000:4000 --mount type=bind,src=$PWD,dst=/root/build --mount type=volume,dst=/root/build/node_modules -it apache/logging_site serve --watch --incremental
```

or run: ```./run-jekyll.sh```

Once it runs, you can reach your website at:

```
http://localhost:4000/
```

Jekyll will regenerate content as you change it and you can see all changes with
hitting refresh.

If you find it necessary to connect to your Docker instance while working, you can run
and connect to it with this command:

```
docker run --rm -p 4000:4000 --mount type=bind,src=$PWD,dst=/root/build --mount type=volume,dst=/root/build/node_modules -it  --entrypoint "/bin/bash" apache/logging_site
```

## Deploying

Once you have committed to this branch, your changes will be built and pushed
to the asf-staging branch. From there, it is published to https://logging.staged.apache.org

If you are happy with your changes, merge the staging branch to the site branch:

```
git checkout asf-site
git merge --ff-only asf-staging
git push
```
