from __future__ import annotations

from typing import Any, Dict, Optional

import boto3

from app.core.config import Settings


class DynamoDBClient:
    def __init__(self, settings: Settings):
        self.settings = settings

        if settings.USE_DYNAMODB_LOCAL and settings.AWS_ENDPOINT_URL:
            self.ddb = boto3.resource(
                "dynamodb",
                region_name=settings.AWS_REGION,
                endpoint_url=settings.AWS_ENDPOINT_URL,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID or "dummy",
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or "dummy",
            )
        else:
            self.ddb = boto3.resource("dynamodb", region_name=settings.AWS_REGION)

        self._table = None

    def table(self, name: Optional[str] = None):
        """Retorna a tabela DynamoDB."""
        if not self._table:
            self._table = self.ddb.Table(name or self.settings.DDB_TABLE)
        return self._table

    def put(self, item: Dict[str, Any]):
        """Insere item na tabela."""
        return self.table().put_item(Item=item)

    def get(self, pk: str, sk: str) -> Optional[Dict[str, Any]]:
        """Busca item por chave primária."""
        response = self.table().get_item(Key={"PK": pk, "SK": sk})
        return response.get("Item")

    def query(self, **kwargs) -> Dict[str, Any]:
        """Executa query na tabela."""
        return self.table().query(**kwargs)

    def update(
        self,
        key: Dict[str, str],
        update_expression: str,
        expression_values: Dict[str, Any],
        expression_names: Optional[Dict[str, str]] = None,
        condition: Optional[str] = None
    ):
        """Atualiza item na tabela."""
        params = {
            "Key": key,
            "UpdateExpression": update_expression,
            "ExpressionAttributeValues": expression_values,
        }
        
        if expression_names:
            params["ExpressionAttributeNames"] = expression_names
            
        if condition:
            params["ConditionExpression"] = condition

        return self.table().update_item(**params)
