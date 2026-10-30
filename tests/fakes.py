"""Dobles de prueba de AWS: cliente DynamoDB de bajo nivel con condiciones y transacciones atómicas,
cliente Bedrock con guion de respuestas y un reloj monotónico controlable."""
import json
import threading


class ClientError(Exception):
    """Imita botocore.exceptions.ClientError (atributo `response`)."""

    def __init__(self, code, reasons=None):
        super().__init__(code)
        self.response = {"Error": {"Code": code, "Message": code}}
        if reasons is not None:
            self.response["CancellationReasons"] = reasons


class ReadTimeoutError(Exception):
    pass


class FakeDynamoClient:
    """Implementa get_item, put_item, delete_item, query y transact_write_items del cliente boto3 `dynamodb`.

    - Las condiciones `attribute_not_exists(pk)` y `#doc = :expected` se evalúan de verdad.
    - Una transacción comprueba todas las condiciones antes de aplicar nada (atomicidad).
    - `fail_next_transaction` simula un fallo de escritura (no se aplica ninguna acción).
    - `before_transaction` permite intercalar otra escritura (concurrencia determinista).
    - Pagina las consultas de `page_size` en `page_size` y registra cada llamada en `calls`.
    """

    page_size = 2

    def __init__(self):
        self.rows = {}
        self.calls = []
        self.lock = threading.RLock()
        self.fail_next_transaction = None
        self.before_transaction = None

    # -- utilidades
    @staticmethod
    def _key(item):
        return item["pk"]["S"], item["sk"]["S"]

    def _check(self, item, condition, values, names):
        key = self._key(item)
        if condition is None:
            return True
        if condition == "attribute_not_exists(pk)":
            return key not in self.rows
        if condition == "#doc = :expected":
            assert names == {"#doc": "doc"}
            current = self.rows.get(key)
            return current is not None and current["doc"]["S"] == values[":expected"]["S"]
        raise AssertionError("condición no soportada: %s" % condition)

    # -- API
    def get_item(self, TableName, Key, ConsistentRead=False):
        assert ConsistentRead is True, "las lecturas deben ser consistentes"
        self.calls.append(("get_item", Key["pk"]["S"]))
        with self.lock:
            found = self.rows.get((Key["pk"]["S"], Key["sk"]["S"]))
            return {"Item": json.loads(json.dumps(found))} if found else {}

    def put_item(self, TableName, Item, ConditionExpression=None, ExpressionAttributeNames=None,
                 ExpressionAttributeValues=None):
        self.calls.append(("put_item", Item["pk"]["S"]))
        with self.lock:
            if not self._check(Item, ConditionExpression, ExpressionAttributeValues, ExpressionAttributeNames):
                raise ClientError("ConditionalCheckFailedException")
            self.rows[self._key(Item)] = json.loads(json.dumps(Item))
        return {}

    def delete_item(self, TableName, Key):
        self.calls.append(("delete_item", Key["pk"]["S"]))
        with self.lock:
            self.rows.pop((Key["pk"]["S"], Key["sk"]["S"]), None)
        return {}

    def query(self, TableName, KeyConditionExpression, ExpressionAttributeValues, ConsistentRead=False,
              ScanIndexForward=True, Limit=None, ExclusiveStartKey=None):
        assert ConsistentRead is True, "las lecturas deben ser consistentes"
        pk = ExpressionAttributeValues[":pk"]["S"]
        prefix = None
        if KeyConditionExpression == "pk = :pk AND begins_with(sk, :prefix)":
            prefix = ExpressionAttributeValues[":prefix"]["S"]
        else:
            assert KeyConditionExpression == "pk = :pk", KeyConditionExpression
        self.calls.append(("query", pk))
        with self.lock:
            keys = sorted(sk for (p, sk) in self.rows if p == pk and (prefix is None or sk.startswith(prefix)))
            if not ScanIndexForward:
                keys.reverse()
            if ExclusiveStartKey:
                start = ExclusiveStartKey["sk"]["S"]
                keys = [k for k in keys if (k > start if ScanIndexForward else k < start)]
            size = min(self.page_size, Limit) if Limit else self.page_size
            page = keys[:size]
            result = {"Items": [json.loads(json.dumps(self.rows[(pk, k)])) for k in page]}
            if len(keys) > size:
                result["LastEvaluatedKey"] = {"pk": {"S": pk}, "sk": {"S": page[-1]}}
            return result

    def transact_write_items(self, TransactItems):
        self.calls.append(("transact", len(TransactItems)))
        if self.before_transaction is not None:
            hook, self.before_transaction = self.before_transaction, None
            hook()
        with self.lock:
            if self.fail_next_transaction is not None:
                error, self.fail_next_transaction = self.fail_next_transaction, None
                raise error
            reasons, ok = [], True
            for action in TransactItems:
                put = action["Put"]
                passed = self._check(put["Item"], put.get("ConditionExpression"), put.get("ExpressionAttributeValues"),
                                     put.get("ExpressionAttributeNames"))
                reasons.append({"Code": "None" if passed else "ConditionalCheckFailed"})
                ok = ok and passed
            if not ok:
                raise ClientError("TransactionCanceledException", reasons)
            for action in TransactItems:
                item = action["Put"]["Item"]
                self.rows[self._key(item)] = json.loads(json.dumps(item))
        return {}

    def count(self, prefix):
        return sum(1 for (pk, _sk) in self.rows if pk.startswith(prefix))


class FakeClock:
    """Reloj monotónico controlable; `sleep` avanza el reloj."""

    def __init__(self, start=1000.0):
        self.now = start
        self.slept = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


class FakeBedrock:
    """Cliente bedrock-runtime simulado. `script` es una lista de textos, excepciones o (texto, segundos)."""

    def __init__(self, *script, clock=None):
        self.script = list(script)
        self.calls = []
        self.clock = clock

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        step = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        if isinstance(step, tuple):
            step, seconds = step
            if self.clock is not None:
                self.clock.now += seconds
        if isinstance(step, Exception):
            raise step
        if isinstance(step, dict):
            return step
        return {"stopReason": "end_turn", "output": {"message": {"role": "assistant", "content": [{"text": step}]}}}
