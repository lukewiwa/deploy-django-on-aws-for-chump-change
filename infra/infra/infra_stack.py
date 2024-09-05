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
    aws_efs as efs,
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

        cluster = ecs.Cluster(
            self, "WiwaCluster", vpc=vpc, enable_fargate_capacity_providers=True
        )
        cloudmap_namespace = cluster.add_default_cloud_map_namespace(
            name="WiwaCloudMap"
        )
        database_persistent_file_system = efs.FileSystem(
            self, "PostgresFileSystem", vpc=vpc
        )
        database_volume_definition = ecs.Volume(
            name="PostgresVolume",
            efs_volume_configuration=ecs.EfsVolumeConfiguration(
                file_system_id=database_persistent_file_system.file_system_id
            ),
        )
        database_task = ecs.TaskDefinition(
            self,
            "WiwaDatabaseDefinition",
            compatibility=ecs.Compatibility.FARGATE,
            memory_mib="1024",
            cpu="512",
            volumes=[database_volume_definition],
        )
        database_container = database_task.add_container(
            "WiwaPostgresDatabase",
            image=ecs.ContainerImage.from_registry(
                "public.ecr.aws/docker/library/postgres:16.4",
            ),
            environment={
                "POSTGRES_PASSWORD": "postgres_password",
                "POSTGRES_USER": "postgres_user",
                "POSTGRES_DB": "postgres_db",
            },
            port_mappings=[ecs.PortMapping(container_port=5432)],
        )
        database_container.add_mount_points(
            ecs.MountPoint(
                container_path="/var/lib/postgresql/data",
                read_only=False,
                source_volume=database_volume_definition.name,
            )
        )
        database_service = ecs.FargateService(
            self,
            "WiwaDatabaseService",
            task_definition=database_task,
            cluster=cluster,
            desired_count=1,
            assign_public_ip=True,
            capacity_provider_strategies=[
                ecs.CapacityProviderStrategy(
                    capacity_provider="FARGATE_SPOT", base=1, weight=1
                )
            ],
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
        )
        database_persistent_file_system.connections.allow_default_port_from(
            database_service
        )
        database_service_endpoint = database_service.enable_cloud_map(
            container=database_container
        )
        task = ecs.TaskDefinition(
            self,
            "WiwaTaskDefinition",
            compatibility=ecs.Compatibility.FARGATE,
            memory_mib="1024",
            cpu="512",
        )
        task.add_container(
            "WiwaDjangoApp",
            image=ecs.ContainerImage.from_asset("../src/"),
            environment={
                "DEBUG": "false",
                "DATABASE_URL": f"psql://postgres_user:postgres_password@{database_service_endpoint.service_name}.{database_service_endpoint.namespace}:5432/postgres_db",
            },
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
