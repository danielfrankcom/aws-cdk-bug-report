import deployments.config as cfg

from aws_cdk import core
from aws_cdk import pipelines
from aws_cdk import aws_codebuild as codebuild
from aws_cdk import aws_codepipeline as codepipeline
from aws_cdk import aws_codepipeline_actions as cpactions
from aws_cdk import aws_lambda as lmb

from function import function
from os import path


class Layer1Stack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        decision_tree_module_path = path.dirname(function.__file__)

        output_path = "/asset-output"
        module_output_path = path.join(output_path, "lib", "function")

        self.function = lmb.Function(
            self,
            id="GetAdapterName",
            code=lmb.Code.from_asset(
                decision_tree_module_path,
                bundling=core.BundlingOptions(
                    image=lmb.Runtime.PYTHON_3_8.bundling_docker_image,
                    command=[
                        "bash",
                        "-c",
                        f"""
                        mkdir -p {module_output_path} &&
                        echo 'from lib.function import function; handler = function.handler' > {output_path}/entry.py &&
                        cp -au . {module_output_path}
                        """,
                    ],
                ),
            ),
            runtime=lmb.Runtime.PYTHON_3_8,
            handler="entry.handler",
        )


class LayerStage(core.Stage):
    def __init__(self, scope: core.Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        l1 = Layer1Stack(self, "Layer1")


class DevelopPipeline(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        source_artifact = codepipeline.Artifact()
        cloud_assembly_artifact = codepipeline.Artifact()

        deployment_pipeline = codepipeline.Pipeline(
            self,
            f"Pipeline-{id}",
            pipeline_name=f"Develop-{id}",
            restart_execution_on_update=True,
            stages=[
                codepipeline.StageOptions(
                    stage_name="Bitbucket-Source-Action",
                    actions=[
                        cpactions.BitBucketSourceAction(
                            action_name="Bitbucket-Commit-Webhook",
                            output=source_artifact,
                            connection_arn=cfg.bitbucket_connection_arn,
                            owner=cfg.repo_owner,
                            repo=cfg.repo_name,
                            branch="develop",
                            code_build_clone_output=True,
                        ),
                    ],
                ),
            ],
        )

        pipeline = pipelines.CdkPipeline(
            self,
            f"STAGING",
            code_pipeline=deployment_pipeline,
            cloud_assembly_artifact=cloud_assembly_artifact,
            synth_action=pipelines.SimpleSynthAction(
                source_artifact=source_artifact,
                cloud_assembly_artifact=cloud_assembly_artifact,
                install_commands=[
                    "npm install -g aws-cdk",
                    "pip install -r requirements.txt",
                ],
                synth_command="cdk synth",
                environment=codebuild.BuildEnvironment(privileged=True),
            ),
        )

        pipeline.add_application_stage(LayerStage(self, "DevelopLayer"))
