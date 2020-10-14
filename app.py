#!/usr/bin/env python3

from aws_cdk import core

from deployments import config
from deployments.develop import DevelopPipeline

app = core.App()

DevelopPipeline(app, "Develop1")
DevelopPipeline(app, "Develop2")

app.synth()
