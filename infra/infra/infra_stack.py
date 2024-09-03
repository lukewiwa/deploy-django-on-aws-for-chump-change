from aws_cdk import (
    Stack,
)
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import (
    aws_ec2 as ec2,
)
from aws_cdk import (
    aws_ecs as ecs,
)
from aws_cdk import (
    aws_rds as rds,
)
from aws_cdk.aws_apigatewayv2_integrations import HttpServiceDiscoveryIntegration
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
        database = rds.DatabaseInstance(
            self,
            "WiwaPostgresDatabase",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_16_3
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
            ),
        )
        cluster = ecs.Cluster(
            self, "WiwaCluster", vpc=vpc, enable_fargate_capacity_providers=True
        )
        task = ecs.TaskDefinition(
            self,
            "WiwaTaskDefinition",
            compatibility=ecs.Compatibility.FARGATE,
            memory_mib="1024",
            cpu="512",
        )
        database.grant_connect(task.task_role)
        task.add_container(
            "WiwaDjangoApp",
            image=ecs.ContainerImage.from_asset("../src/"),
            environment={"DEBUG": "false"},
            port_mappings=[ecs.PortMapping(container_port=8000)],
        )
        service = ecs.FargateService(
            self,
            "WiwaService",
            task_definition=task,
            cluster=cluster,
            desired_count=1,
            capacity_provider_strategies=[
                ecs.CapacityProviderStrategy(
                    capacity_provider="FARGATE_SPOT", base=1, weight=1
                )
            ],
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
        )
        cloudmap_namespace = cluster.add_default_cloud_map_namespace(
            name="WiwaCloudMap"
        )
        service_endpoint = service.enable_cloud_map(
            cloud_map_namespace=cloudmap_namespace
        )
        vpc_link = apigwv2.VpcLink(
            self,
            "VPCLink",
            vpc=vpc,
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
        )
        apigwv2.HttpApi(
            self,
            "HttpProxyPrivateApi",
            default_integration=HttpServiceDiscoveryIntegration(
                "DefaultIntegration", service_endpoint, vpc_link=vpc_link
            ),
        )

        # WAF maybe
