from aws_cdk import (
    Stack,
)
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import (
    aws_ec2 as ec2,
)
from aws_cdk import (
    aws_efs as efs,
)
from aws_cdk import (
    aws_lambda as lambda_,
)
from aws_cdk.aws_apigatewayv2_integrations import (
    HttpLambdaIntegration,
)
from constructs import Construct


class InfraStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        vpc = ec2.Vpc(
            self,
            "Vpc",
            vpc_name="WiwaVpc",
            max_azs=1,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="WiwaPublicSubnet", subnet_type=ec2.SubnetType.PUBLIC
                ),
                ec2.SubnetConfiguration(
                    name="WiwaPrivateSubnet",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                ),
            ],
        )

        app_persistent_file_system = efs.FileSystem(self, "AppFileSystem", vpc=vpc)
        access_point = app_persistent_file_system.add_access_point(
            "AccessPoint",
            path="/export/lambda",
            create_acl=efs.Acl(owner_uid="1001", owner_gid="1001", permissions="750"),
            posix_user=efs.PosixUser(uid="1001", gid="1001"),
        )
        function = lambda_.DockerImageFunction(
            self,
            "WiwaFunction",
            code=lambda_.DockerImageCode.from_image_asset("../src"),
            environment={
                "DEBUG": "false",
                "DATABASE_URL": "sqlite:////mnt/db/sqlite.db",
            },
            vpc=vpc,
            filesystem=lambda_.FileSystem.from_efs_access_point(
                access_point, "/mnt/db"
            ),
        )
        integration = HttpLambdaIntegration("LambdaIntegration", function)
        apigwv2.HttpApi(
            self,
            "HttpProxyPrivateApi",
            default_integration=integration,
            create_default_stage=True
        )

        # WAF maybe
