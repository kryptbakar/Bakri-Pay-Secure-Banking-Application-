import logging

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from werkzeug.exceptions import BadRequest, NotFound, Forbidden
from flask_login import login_required, current_user

from app.services.transaction_service import TransactionService
from app.utils.validators import validate_amount, InvalidInputError

transactions_bp = Blueprint('transactions', __name__)
logger = logging.getLogger(__name__)


@transactions_bp.route('/', methods=['GET'])
@login_required
def get_transactions():
    """Get transaction history for user"""
    try:
        account_id = request.args.get('account_id')
        limit = min(int(request.args.get('limit', 50)), 100)
        offset = int(request.args.get('offset', 0))

        transactions = TransactionService.get_transaction_history(
            user_id=current_user.user_id,
            account_id=account_id,
            limit=limit,
            offset=offset
        )

        if request.is_json or request.headers.get('Accept') == 'application/json':
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
        else:
            return render_template('transactions.html',
                                transactions=transactions,
                                account_id=account_id,
                                limit=limit,
                                offset=offset)

    except Exception as e:
        logger.error(f"Failed to get transactions: {str(e)}")
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': 'Failed to retrieve transactions', 'code': 'SERVER_ERROR'}), 500
        else:
            flash('Failed to retrieve transactions', 'danger')
            return redirect(url_for('accounts.dashboard'))


@transactions_bp.route('/<transaction_id>', methods=['GET'])
@login_required
def get_transaction_details(transaction_id):
    """Get details of a specific transaction"""
    try:
        transaction = TransactionService.get_transaction_details(current_user.user_id, transaction_id)

        if request.is_json or request.headers.get('Accept') == 'application/json':
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
        else:
            return render_template('transaction_details.html', transaction=transaction)

    except NotFound as e:
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': str(e), 'code': 'TRANSACTION_NOT_FOUND'}), 404
        else:
            flash('Transaction not found', 'danger')
            return redirect(url_for('transactions.get_transactions'))
    except Forbidden as e:
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': str(e), 'code': 'UNAUTHORIZED_ACCESS'}), 403
        else:
            flash('You do not have access to this transaction', 'danger')
            return redirect(url_for('transactions.get_transactions'))
    except Exception as e:
        logger.error(f"Failed to get transaction {transaction_id}: {str(e)}")
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': 'Failed to retrieve transaction', 'code': 'SERVER_ERROR'}), 500
        else:
            flash('Failed to retrieve transaction details', 'danger')
            return redirect(url_for('transactions.get_transactions'))


@transactions_bp.route('/', methods=['POST'])
@login_required
def create_transaction():
    """Create a new transaction (transfer, deposit, etc.)"""
    try:
        data = request.form
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if not data or 'type' not in data:
            raise BadRequest(description='Transaction type is required')

        # Validate based on transaction type
        if data['type'] == 'transfer':
            required_fields = ['from_account', 'to_account', 'amount']
            if not all(field in data for field in required_fields):
                raise BadRequest(description=f'Transfer requires: {required_fields}')

            try:
                amount = validate_amount(data['amount'])
            except InvalidInputError as e:
                raise BadRequest(description=e.message)

            transaction = TransactionService.transfer_funds(
                user_id=current_user.user_id,
                from_account_id=data['from_account'],
                to_account_id=data['to_account'],
                amount=amount,
                reference=data.get('reference', '')
            )
        elif data['type'] == 'deposit':
            required_fields = ['to_account', 'amount']
            if not all(field in data for field in required_fields):
                raise BadRequest(description=f'Deposit requires: {required_fields}')

            try:
                amount = validate_amount(data['amount'])
            except InvalidInputError as e:
                raise BadRequest(description=e.message)

            transaction = TransactionService.create_deposit(
                user_id=current_user.user_id,
                account_id=data['to_account'],
                amount=amount,
                reference=data.get('reference', '')
            )
        else:
            raise BadRequest(description='Invalid transaction type')

        logger.info(f"Transaction created: {transaction.transaction_id}")

        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({
                'transaction_id': str(transaction.transaction_id),
                'status': transaction.status,
                'amount': float(transaction.amount),
                'type': transaction.transaction_type,
                'timestamp': transaction.created_at.isoformat()
            }), 201
        else:
            flash('Transaction created successfully', 'success')
            if transaction.transaction_type == 'transfer':
                return redirect(url_for('accounts.get_account_details', account_id=data['from_account']))
            else:
                return redirect(url_for('accounts.get_account_details', account_id=data['to_account']))

    except BadRequest as e:
        logger.warning(f"Invalid transaction request: {str(e)}")
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': str(e), 'code': 'VALIDATION_ERROR'}), 400
        else:
            flash(str(e), 'danger')
            return redirect(url_for('accounts.dashboard'))
    except Forbidden as e:
        logger.warning(f"Unauthorized transaction attempt by user {current_user.user_id}")
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': str(e), 'code': 'UNAUTHORIZED_ACCESS'}), 403
        else:
            flash('Unauthorized account access', 'danger')
            return redirect(url_for('accounts.dashboard'))
    except ValueError as e:
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': str(e), 'code': 'INVALID_AMOUNT'}), 400
        else:
            flash(str(e), 'danger')
            return redirect(url_for('accounts.dashboard'))
    except Exception as e:
        logger.error(f"Transaction failed: {str(e)}", exc_info=True)
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': 'Transaction failed', 'code': 'SERVER_ERROR'}), 500
        else:
            flash('Transaction failed', 'danger')
            return redirect(url_for('accounts.dashboard'))