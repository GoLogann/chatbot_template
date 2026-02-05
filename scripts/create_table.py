import boto3
from botocore.exceptions import ClientError

from app.core.config import Settings


def get_dynamodb_client():
    """Retorna cliente DynamoDB baseado na configuração"""
    settings = Settings()

    if settings.USE_DYNAMODB_LOCAL and settings.AWS_ENDPOINT_URL:
        print(f"🔧 Conectando ao DynamoDB Local: {settings.AWS_ENDPOINT_URL}")
        return boto3.client(
            "dynamodb",
            region_name=settings.AWS_REGION,
            endpoint_url=settings.AWS_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID or "dummy",
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or "dummy",
        ), settings

    session = (
        boto3.Session(
            # profile_name=settings.AWS_PROFILE,
            region_name=settings.AWS_REGION,
        )
        if settings.AWS_PROFILE
        else boto3.Session(region_name=settings.AWS_REGION)
    )
    return session.client("dynamodb"), settings


def ensure_table():
    dynamodb, settings = get_dynamodb_client()
    table_name = settings.DDB_TABLE

    try:
        print(f"➡️ Criando tabela '{table_name}' em {settings.AWS_REGION}...")

        params = {
            "TableName": table_name,
            "BillingMode": "PAY_PER_REQUEST",
            "AttributeDefinitions": [
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
                {"AttributeName": "GSI1PK", "AttributeType": "S"},
                {"AttributeName": "GSI1SK", "AttributeType": "S"},
                {"AttributeName": "GSI2PK", "AttributeType": "S"},
                {"AttributeName": "GSI2SK", "AttributeType": "S"},
                {"AttributeName": "GSI3PK", "AttributeType": "S"},
                {"AttributeName": "GSI3SK", "AttributeType": "S"},
                {"AttributeName": "GSI4PK", "AttributeType": "S"},
                {"AttributeName": "GSI4SK", "AttributeType": "S"},
            ],
            "KeySchema": [
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            "GlobalSecondaryIndexes": [
                {
                    "IndexName": "GSI1",
                    "KeySchema": [
                        {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "GSI2",
                    "KeySchema": [
                        {"AttributeName": "GSI2PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI2SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "GSI3",
                    "KeySchema": [
                        {"AttributeName": "GSI3PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI3SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
                {
                    "IndexName": "GSI4",
                    "KeySchema": [
                        {"AttributeName": "GSI4PK", "KeyType": "HASH"},
                        {"AttributeName": "GSI4SK", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                },
            ],
        }

        if not settings.USE_DYNAMODB_LOCAL:
            params["StreamSpecification"] = {
                "StreamEnabled": True,
                "StreamViewType": "NEW_AND_OLD_IMAGES",
            }
            params["SSESpecification"] = {"Enabled": False}
            params["Tags"] = [
                {"Key": "Name", "Value": f"{table_name}-{getattr(settings, 'ENV', 'dev')}"},
                {"Key": "Project", "Value": "ChatbotTemplate"},
                {"Key": "Env", "Value": getattr(settings, "ENV", "dev")},
            ]

        dynamodb.create_table(**params)

        waiter = dynamodb.get_waiter("table_exists")
        waiter.wait(TableName=table_name)
        print("✅ Tabela criada com sucesso!")

    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"ℹ️ Tabela '{table_name}' já existe. Pulando criação.")
        else:
            print(f"❌ Erro ao criar tabela: {e}")
            raise


# def enable_pitr():
#     """Habilita Point-in-Time Recovery (só no AWS real)"""
#     _, settings = get_dynamodb_client()

#     if settings.USE_DYNAMODB_LOCAL:
#         print("⚠️ PITR não é suportado no DynamoDB Local. Pulando...")
#         return

#     dynamodb, settings = get_dynamodb_client()

#     try:
#         dynamodb.update_continuous_backups(
#             TableName=settings.DDB_TABLE,
#             PointInTimeRecoverySpecification={"PointInTimeRecoveryEnabled": True},
#         )
#         print("✅ PITR habilitado.")
#     except ClientError as e:
#         print(f"⚠️ Erro no PITR: {e}")


def list_tables():
    """Lista todas as tabelas"""
    dynamodb, _ = get_dynamodb_client()
    response = dynamodb.list_tables()
    print("📋 Tabelas disponíveis:")
    for table in response.get("TableNames", []):
        print(f"  - {table}")


if __name__ == "__main__":
    ensure_table()
    # enable_pitr()
    list_tables()
