import logging

from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest, NotFound, Forbidden

from ..services.transaction_service import TransactionService
from ..utils.security import login_required, get_current_user_id

transactions_bp = Blueprint('transactions', __name__)
logger = logging.getLogger(__name__)


@transactions_bp.route('/', methods=['POST'])
@login_required
def create_transaction():
    """
    Create a new transaction (transfer, deposit, etc.)
    ---
    tags:
      - Transactions
    parameters:
      - name: body
        in: body
        required: true
        schema:
          $ref: '#/definitions/TransactionRequest'
    responses:
      201:
        description: Transaction created successfully
        schema:
          $ref: '#/definitions/Transaction'
      400:
        $ref: '#/responses/BadRequest'
      401:
        $ref: '#/responses/Unauthorized'
      403:
        $ref: '#/responses/Forbidden'
    """
    try:
        user_id = get_current_user_id()
        data = request.get_json()

        if not data or 'type' not in data:
            raise BadRequest(description='Transaction type is required')

        # Validate based on transaction type
        if data['type'] == 'transfer':
            required_fields = ['from_account', 'to_account', 'amount']
            if not all(field in data for field in required_fields):
                raise BadRequest(description=f'Transfer requires: {required_fields}')

            transaction = TransactionService.transfer_funds(
                user_id=user_id,
                from_account_id=data['from_account'],
                to_account_id=data['to_account'],
                amount=data['amount'],
                reference=data.get('reference', '')
            )
        elif data['type'] == 'deposit':
            required_fields = ['to_account', 'amount']
            if not all(field in data for field in required_fields):
                raise BadRequest(description=f'Deposit requires: {required_fields}')

            transaction = TransactionService.create_deposit(
                user_id=user_id,
                account_id=data['to_account'],
                amount=data['amount'],
                reference=data.get('reference', '')
            )
        else:
            raise BadRequest(description='Invalid transaction type')

        logger.info(f"Transaction created: {transaction.transaction_id}")
        return jsonify({
            'transaction_id': str(transaction.transaction_id),
            'status': transaction.status,
            'amount': float(transaction.amount),
            'type': transaction.transaction_type,
            'timestamp': transaction.created_at.isoformat()
        }), 201

    except BadRequest as e:
        logger.warning(f"Invalid transaction request: {str(e)}")
        return jsonify({'error': str(e), 'code': 'VALIDATION_ERROR'}), 400
    except Forbidden as e:
        logger.warning(f"Unauthorized transaction attempt by user {user_id}")
        return jsonify({'error': str(e), 'code': 'UNAUTHORIZED_ACCESS'}), 403
    except ValueError as e:
        return jsonify({'error': str(e), 'code': 'INVALID_AMOUNT'}), 400
    except Exception as e:
        logger.error(f"Transaction failed: {str(e)}", exc_info=True)
        return jsonify({'error': 'Transaction failed', 'code': 'SERVER_ERROR'}), 500


@transactions_bp.route('/', methods=['GET'])
@login_required
def get_transactions():
    """
    Get transaction history for user
    ---
    tags:
      - Transactions
    parameters:
      - name: account_id
        in: query
        type: string
      - name: limit
        in: query
        type: integer
      - name: offset
        in: query
        type: integer
    responses:
      200:
        description: List of transactions
        schema:
          type: array
          items:
            $ref: '#/definitions/Transaction'
      401:
        $ref: '#/responses/Unauthorized'
    """
    try:
        user_id = get_current_user_id()
        account_id = request.args.get('account_id')
        limit = min(int(request.args.get('limit', 50)), 100)
        offset = int(request.args.get('offset', 0))

        transactions = TransactionService.get_transaction_history(
            user_id=user_id,
            account_id=account_id,
            limit=limit,
            offset=offset
        )

        return jsonify([{
            'transaction_id': str(txn.transaction_id),
            'amount': float(txn.amount),
            'type': txn.transaction_type,
            'status': txn.status,
            'reference': txn.reference,
            'timestamp': txn.created_at.isoformat(),
            'from_account': str(txn.from_account_id) if txn.from_account_id else None,
            'to_account': str(txn.to_account_id)
        } for txn in transactions]), 200

    except Exception as e:
        logger.error(f"Failed to get transactions: {str(e)}")
        return jsonify({'error': 'Failed to retrieve transactions', 'code': 'SERVER_ERROR'}), 500


@transactions_bp.route('/<transaction_id>', methods=['GET'])
@login_required
def get_transaction_details(transaction_id):
    """
    Get details of a specific transaction
    ---
    tags:
      - Transactions
    parameters:
      - name: transaction_id
        in: path
        required: true
        type: string
    responses:
      200:
        description: Transaction details
        schema:
          $ref: '#/definitions/TransactionDetails'
      401:
        $ref: '#/responses/Unauthorized'
      404:
        $ref: '#/responses/NotFound'
    """
    try:
        user_id = get_current_user_id()
        transaction = TransactionService.get_transaction_details(user_id, transaction_id)

        return jsonify({
            'transaction_id': str(transaction.transaction_id),
            'amount': float(transaction.amount),
            'type': transaction.transaction_type,
            'status': transaction.status,
            'reference': transaction.reference,
            'timestamp': transaction.created_at.isoformat(),
            'from_account': {
                'account_id': str(transaction.from_account_id),
                'number': transaction.sender_account.account_number if transaction.sender_account else None
            } if transaction.from_account_id else None,
            'to_account': {
                'account_id': str(transaction.to_account_id),
                'number': transaction.receiver_account.account_number
            },
            'is_fraudulent': transaction.is_fraudulent
        }), 200

    except NotFound as e:
        return jsonify({'error': str(e), 'code': 'TRANSACTION_NOT_FOUND'}), 404
    except Forbidden as e:
        return jsonify({'error': str(e), 'code': 'UNAUTHORIZED_ACCESS'}), 403
    except Exception as e:
        logger.error(f"Failed to get transaction {transaction_id}: {str(e)}")
        return jsonify({'error': 'Failed to retrieve transaction', 'code': 'SERVER_ERROR'}), 500
