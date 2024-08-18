from aws_cdk import (
    Stack,
)
from aws_cdk import (
    aws_ec2 as ec2,
)
from aws_cdk import (
    aws_ecs as ecs,
)
from aws_cdk import (
    aws_elasticloadbalancingv2 as elbv2,
)
from aws_cdk import (
    aws_rds as rds,
)
from constructs import Construct


class InfraStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        vpc = ec2.Vpc(self, "Vpc", vpc_name="WiwaVpc")
        database = rds.DatabaseInstance(
            self,
            "WiwaPostgresDatabase",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_16_3
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT
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
        container = task.add_container(
            "WiwaDjangoApp",
            image=ecs.ContainerImage.from_asset("../src/"),
            environment={"DEBUG": "false"},
            port_mappings=[ecs.PortMapping(container_port=8000)],
        )
        service = ecs.FargateService(
            self, "WiwaService", task_definition=task, cluster=cluster
        )
        lb = elbv2.ApplicationLoadBalancer(
            self, "WiwaLB", vpc=vpc, internet_facing=True
        )
        listener = lb.add_listener("Listener", port=80)
        listener.add_targets(
            "EcsDjangoContainer",
            port=8000,
            targets=[
                service.load_balancer_target(container_name=container.container_name)
            ],
        )

        # WAF maybe
