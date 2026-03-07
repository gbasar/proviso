
# Envbironment
Build time
## The Build-Time Layer (ARG)

This is the "inheritance" that happens while you are creating the image, ARG variables are only available during the docker build process. 
If you have a base image with an ARG, a child image (using FROM base-image) can inherit it if it's declared globally, but typically ARG is used to pass versions (like JDK_VERSION) into the build.

Limitation: Once the image is built, ARG variables vanish. They are not available when the container is actually running.




##  The Image Layer (ENV)

This is the most common form of inheritance in Docker. When you define an ENV in a Dockerfile, it becomes a permanent part of that image and any image that uses it as a base.

Inheritance: If you have a base image with ENV JAVA_HOME=/opt/java and you create a new Dockerfile starting with FROM base-image, your new image inherits that variable automatically.

Override: You can "deselect" or change it by simply declaring ENV JAVA_HOME=/opt/jdk-21 in your new Dockerfile. The last definition wins.

## The Runtime Layer (-e or .env files)

This is where the "mode" switching happens, similar to what you were looking for with your shell. When you start a container, you can inject variables that override everything baked into the image.

Command Line: docker run -e MODE=production -e JDK_VERSION=19 my-image

Docker Compose: You can use a .env file to manage these. Compose handles the "merging" of your local environment variables into the container's environment.

How "Deselection" Works in Docker

Unlike a shell session where you unset a variable, in Docker, environment variables are generally immutable for the life of the container.

To "deselect" a mode: You don't change the variable inside the running container; you stop the container and start a new one with different flags.

The "Null" Override: If an image has an ENV you don't want, you can't truly "delete" it from the OS, but you can override it with an empty string: docker run -e UNWANTED_VAR="" my-image.

Docker + HOCON Pattern

If you were to use your HOCON-driven Rust tool with Docker, your workflow would look like this:

Rust Tool: Merges base.conf and mode.conf into a flat list of key-value pairs.

Output: Generates a .env file.

Docker: docker compose --env-file ./my-generated.env up.

This allows you to keep your complex HOCON logic on your host machine while feeding Docker the simple flat list of variables it requires.

Summary of Priority

If the same variable is defined in multiple places, Docker follows this "closeness to execution" rule:

Runtime flags (docker run -e ...) — Highest Priority

Docker Compose .env file