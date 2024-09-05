from aws_cdk import (
    Stack,
)
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import (
    aws_ec2 as ec2,
)
from aws_cdk import (
    aws_lambda as lambda_,
)
from aws_cdk import (
    aws_s3 as s3,
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

        database_bucket = s3.Bucket(
            self, "DatabaseBucket", block_public_access=s3.BlockPublicAccess.BLOCK_ALL
        )
        function = lambda_.DockerImageFunction(
            self,
            "WiwaFunction",
            code=lambda_.DockerImageCode.from_image_asset("../src"),
            environment={
                "DEBUG": "false",
                "DATABASE_URL": "sqlite:////tmp/sqlite.db",
                "SQLITE_OBJECT_STORAGE_BUCKET_NAME": database_bucket.bucket_name,
            },
            vpc=vpc,
        )
        database_bucket.grant_read_write(function)
        integration = HttpLambdaIntegration("LambdaIntegration", function)
        apigwv2.HttpApi(
            self,
            "HttpProxyPrivateApi",
            default_integration=integration,
            create_default_stage=True,
        )

        # WAF maybe
