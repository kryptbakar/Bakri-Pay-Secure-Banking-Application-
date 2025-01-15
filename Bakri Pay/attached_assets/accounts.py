import logging

from flask import Blueprint, request, jsonify
from werkzeug.exceptions import NotFound, Forbidden, BadRequest

from ..services.account_service import AccountService
from ..utils.security import login_required, get_current_user_id

accounts_bp = Blueprint('accounts', __name__)
logger = logging.getLogger(__name__)


@accounts_bp.route('/', methods=['GET'])
@login_required
def get_accounts():
    """
    Get all accounts for the authenticated user
    ---
    tags:
      - Accounts
    responses:
      200:
        description: List of user accounts
        schema:
          type: array
          items:
            $ref: '#/definitions/Account'
      401:
        $ref: '#/responses/Unauthorized'
      500:
        $ref: '#/responses/ServerError'
    """
    try:
        user_id = get_current_user_id()
        accounts = AccountService.get_user_accounts(user_id)

        logger.info(f"Retrieved accounts for user {user_id}")
        return jsonify([{
            'account_id': str(acc.account_id),
            'account_number': acc.account_number,
            'balance': float(acc.balance),
            'status': acc.status,
            'created_at': acc.created_at.isoformat()
        } for acc in accounts]), 200

    except Exception as e:
        logger.error(f"Failed to get accounts for user {user_id}: {str(e)}")
        return jsonify({'error': 'Failed to retrieve accounts', 'code': 'SERVER_ERROR'}), 500


@accounts_bp.route('/<account_id>', methods=['GET'])
@login_required
def get_account_details(account_id):
    """
    Get detailed information for a specific account
    ---
    tags:
      - Accounts
    parameters:
      - name: account_id
        in: path
        required: true
        type: string
    responses:
      200:
        description: Account details
        schema:
          $ref: '#/definitions/Account'
      401:
        $ref: '#/responses/Unauthorized'
      403:
        $ref: '#/responses/Forbidden'
      404:
        $ref: '#/responses/NotFound'
    """
    try:
        user_id = get_current_user_id()
        account = AccountService.get_account_details(user_id, account_id)

        return jsonify({
            'account_id': str(account.account_id),
            'account_number': account.account_number,
            'balance': float(account.balance),
            'status': account.status,
            'created_at': account.created_at.isoformat(),
            'cards': [{
                'card_id': str(card.card_id),
                'last_four': card.card_number[-4:],
                'is_virtual': card.is_virtual,
                'is_active': card.is_active
            } for card in account.cards]
        }), 200

    except NotFound as e:
        return jsonify({'error': str(e), 'code': 'ACCOUNT_NOT_FOUND'}), 404
    except Forbidden as e:
        return jsonify({'error': str(e), 'code': 'UNAUTHORIZED_ACCESS'}), 403
    except Exception as e:
        logger.error(f"Failed to get account {account_id}: {str(e)}")
        return jsonify({'error': 'Failed to retrieve account', 'code': 'SERVER_ERROR'}), 500


@accounts_bp.route('/', methods=['POST'])
@login_required
def create_account():
    """
    Create a new account for the authenticated user
    ---
    tags:
      - Accounts
    responses:
      201:
        description: Account created successfully
        schema:
          $ref: '#/definitions/Account'
      401:
        $ref: '#/responses/Unauthorized'
      500:
        $ref: '#/responses/ServerError'
    """
    try:
        user_id = get_current_user_id()
        account = AccountService.create_account(user_id)

        logger.info(f"Created new account {account.account_id} for user {user_id}")
        return jsonify({
            'account_id': str(account.account_id),
            'account_number': account.account_number,
            'message': 'Account created successfully'
        }), 201

    except Exception as e:
        logger.error(f"Failed to create account for user {user_id}: {str(e)}")
        return jsonify({'error': 'Failed to create account', 'code': 'SERVER_ERROR'}), 500


@accounts_bp.route('/<account_id>/balance', methods=['GET'])
@login_required
def get_balance(account_id):
    """
    Get account balance
    ---
    tags:
      - Accounts
    parameters:
      - name: account_id
        in: path
        required: true
        type: string
    responses:
      200:
        description: Account balance
        schema:
          type: object
          properties:
            balance:
              type: number
              format: float
      401:
        $ref: '#/responses/Unauthorized'
      403:
        $ref: '#/responses/Forbidden'
      404:
        $ref: '#/responses/NotFound'
    """
    try:
        user_id = get_current_user_id()
        balance = AccountService.get_account_balance(user_id, account_id)

        return jsonify({
            'account_id': str(account_id),
            'balance': float(balance)
        }), 200

    except NotFound as e:
        return jsonify({'error': str(e), 'code': 'ACCOUNT_NOT_FOUND'}), 404
    except Forbidden as e:
        return jsonify({'error': str(e), 'code': 'UNAUTHORIZED_ACCESS'}), 403
    except Exception as e:
        logger.error(f"Failed to get balance for account {account_id}: {str(e)}")
        return jsonify({'error': 'Failed to retrieve balance', 'code': 'SERVER_ERROR'}), 500


@accounts_bp.route('/<account_id>/transfer', methods=['POST'])
@login_required
def transfer_funds(account_id):
    """
    Transfer funds from an account
    ---
    tags:
      - Accounts
    parameters:
      - name: account_id
        in: path
        required: true
        type: string
      - name: body
        in: body
        required: true
        schema:
          $ref: '#/definitions/TransferRequest'
    responses:
      200:
        description: Transfer successful
        schema:
          $ref: '#/definitions/TransferResponse'
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

        if not data or 'to_account' not in data or 'amount' not in data:
            raise BadRequest(description='Missing required fields: to_account and amount')

        transaction = AccountService.transfer_funds(
            source_account_id=account_id,
            target_account_id=data['to_account'],
            amount=data['amount'],
            reference=data.get('reference', '')
        )

        logger.info(f"Transfer from {account_id} to {data['to_account']} for amount {data['amount']}")
        return jsonify({
            'transaction_id': str(transaction.transaction_id),
            'amount': float(transaction.amount),
            'status': transaction.status,
            'reference': transaction.reference
        }), 200

    except BadRequest as e:
        return jsonify({'error': str(e), 'code': 'VALIDATION_ERROR'}), 400
    except NotFound as e:
        return jsonify({'error': str(e), 'code': 'ACCOUNT_NOT_FOUND'}), 404
    except Forbidden as e:
        return jsonify({'error': str(e), 'code': 'UNAUTHORIZED_ACCESS'}), 403
    except ValueError as e:
        return jsonify({'error': str(e), 'code': 'INVALID_AMOUNT'}), 400
    except Exception as e:
        logger.error(f"Transfer failed: {str(e)}")
        return jsonify({'error': 'Transfer failed', 'code': 'SERVER_ERROR'}), 500
