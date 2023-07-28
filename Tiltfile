# -*- mode: Python -*-

allow_k8s_contexts('docker-desktop')

load('ext://helm_resource', 'helm_resource', 'helm_repo')

helm_repo("twuni", "https://helm.twun.io")
helm_resource(
  "registry",
  "twuni/docker-registry",
  flags=["-f", "./environments/tilt/registry-values.yaml"],
  port_forwards=[5000],
  resource_deps=["twuni"],
)

docker_build(
  "build-server",
  context="./servers/remote-build",
  match_in_env_vars=True,
)

helm_resource(
  "chassis-build-server",
  chart="./servers/remote-build/charts/chassis-build-server",
  image_deps=["build-server"],
  image_keys=[("image.repository", "image.tag")],
  flags=["-f", "./environments/tilt/build-server-values.yaml"],
  port_forwards=[8080],
  deps=["./environments/tilt/build-server-values.yaml"],
)
