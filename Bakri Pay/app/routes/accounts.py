import logging

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session, flash
from werkzeug.exceptions import NotFound, Forbidden, BadRequest
from flask_login import login_required, current_user

from app.services.account_service import AccountService
from app.utils.validators import validate_amount, InvalidInputError

accounts_bp = Blueprint('accounts', __name__)
logger = logging.getLogger(__name__)


@accounts_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard page with account overview"""
    try:
        accounts = AccountService.get_user_accounts(current_user.user_id)
        return render_template('dashboard.html', accounts=accounts)
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        flash('Unable to load dashboard data', 'danger')
        return redirect(url_for('auth.login'))


@accounts_bp.route('/', methods=['GET'])
@login_required
def get_accounts():
    """API to get all accounts for the authenticated user"""
    try:
        accounts = AccountService.get_user_accounts(current_user.user_id)

        logger.info(f"Retrieved accounts for user {current_user.user_id}")
        
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify([{
                'account_id': str(acc.account_id),
                'account_number': acc.account_number,
                'balance': float(acc.balance),
                'status': acc.status,
                'created_at': acc.created_at.isoformat()
            } for acc in accounts]), 200
        else:
            return render_template('accounts.html', accounts=accounts)

    except Exception as e:
        logger.error(f"Failed to get accounts for user {current_user.user_id}: {str(e)}")
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({
                'error': 'Failed to retrieve accounts',
                'code': 'SERVER_ERROR'
            }), 500
        else:
            flash('Failed to retrieve accounts', 'danger')
            return redirect(url_for('accounts.dashboard'))


@accounts_bp.route('/<account_id>', methods=['GET'])
@login_required
def get_account_details(account_id):
    """Get detailed information for a specific account"""
    try:
        account = AccountService.get_account_details(current_user.user_id, account_id)
        
        if request.is_json or request.headers.get('Accept') == 'application/json':
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
        else:
            return render_template('account_details.html', account=account)

    except NotFound as e:
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': str(e), 'code': 'ACCOUNT_NOT_FOUND'}), 404
        else:
            flash('Account not found', 'danger')
            return redirect(url_for('accounts.get_accounts'))
    except Forbidden as e:
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': str(e), 'code': 'UNAUTHORIZED_ACCESS'}), 403
        else:
            flash('You do not have access to this account', 'danger')
            return redirect(url_for('accounts.get_accounts'))
    except Exception as e:
        logger.error(f"Failed to get account {account_id}: {str(e)}")
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': 'Failed to retrieve account', 'code': 'SERVER_ERROR'}), 500
        else:
            flash('Failed to retrieve account details', 'danger')
            return redirect(url_for('accounts.get_accounts'))


@accounts_bp.route('/', methods=['POST'])
@login_required
def create_account():
    """Create a new account for the authenticated user"""
    try:
        account = AccountService.create_account(current_user.user_id)

        logger.info(f"Created new account {account.account_id} for user {current_user.user_id}")
        
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({
                'account_id': str(account.account_id),
                'account_number': account.account_number,
                'message': 'Account created successfully'
            }), 201
        else:
            flash('Account created successfully', 'success')
            return redirect(url_for('accounts.get_accounts'))

    except Exception as e:
        logger.error(f"Failed to create account for user {current_user.user_id}: {str(e)}")
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': 'Failed to create account', 'code': 'SERVER_ERROR'}), 500
        else:
            flash('Failed to create account', 'danger')
            return redirect(url_for('accounts.dashboard'))


@accounts_bp.route('/<account_id>/balance', methods=['GET'])
@login_required
def get_balance(account_id):
    """Get account balance"""
    try:
        balance = AccountService.get_account_balance(current_user.user_id, account_id)

        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({
                'account_id': str(account_id),
                'balance': float(balance)
            }), 200
        else:
            return render_template('account_balance.html', 
                                 account_id=account_id, 
                                 balance=balance)

    except NotFound as e:
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': str(e), 'code': 'ACCOUNT_NOT_FOUND'}), 404
        else:
            flash('Account not found', 'danger')
            return redirect(url_for('accounts.get_accounts'))
    except Forbidden as e:
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': str(e), 'code': 'UNAUTHORIZED_ACCESS'}), 403
        else:
            flash('You do not have access to this account', 'danger')
            return redirect(url_for('accounts.get_accounts'))
    except Exception as e:
        logger.error(f"Failed to get balance for account {account_id}: {str(e)}")
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': 'Failed to retrieve balance', 'code': 'SERVER_ERROR'}), 500
        else:
            flash('Failed to retrieve balance', 'danger')
            return redirect(url_for('accounts.get_accounts'))


@accounts_bp.route('/<account_id>/transfer', methods=['GET', 'POST'])
@login_required
def transfer_funds(account_id):
    """Transfer funds from an account"""
    
    # GET request - show transfer form
    if request.method == 'GET':
        try:
            # Check account ownership
            account = AccountService.get_account_details(current_user.user_id, account_id)
            return render_template('transfer.html', account=account)
        except Exception as e:
            flash('Unable to access account', 'danger')
            return redirect(url_for('accounts.get_accounts'))
    
    # POST request - process transfer
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
            
        if not data or 'to_account' not in data or 'amount' not in data:
            raise BadRequest(description='Missing required fields: to_account and amount')
            
        # Validate and convert amount
        try:
            amount = validate_amount(data['amount'])
        except InvalidInputError as e:
            raise BadRequest(description=e.message)
            
        # Process transfer
        transaction = AccountService.transfer_funds(
            source_account_id=account_id,
            target_account_id=data['to_account'],
            amount=amount,
            reference=data.get('reference', '')
        )

        logger.info(f"Transfer from {account_id} to {data['to_account']} for amount {amount}")
        
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({
                'transaction_id': str(transaction.transaction_id),
                'amount': float(transaction.amount),
                'status': transaction.status,
                'reference': transaction.reference
            }), 200
        else:
            flash('Transfer completed successfully', 'success')
            return redirect(url_for('accounts.get_account_details', account_id=account_id))

    except BadRequest as e:
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': str(e), 'code': 'VALIDATION_ERROR'}), 400
        else:
            flash(str(e), 'danger')
            return redirect(url_for('accounts.transfer_funds', account_id=account_id))
    except NotFound as e:
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': str(e), 'code': 'ACCOUNT_NOT_FOUND'}), 404
        else:
            flash('Account not found', 'danger')
            return redirect(url_for('accounts.transfer_funds', account_id=account_id))
    except Forbidden as e:
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': str(e), 'code': 'UNAUTHORIZED_ACCESS'}), 403
        else:
            flash('Unauthorized access to account', 'danger')
            return redirect(url_for('accounts.dashboard'))
    except ValueError as e:
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': str(e), 'code': 'INVALID_AMOUNT'}), 400
        else:
            flash(str(e), 'danger')
            return redirect(url_for('accounts.transfer_funds', account_id=account_id))
    except Exception as e:
        logger.error(f"Transfer failed: {str(e)}")
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': 'Transfer failed', 'code': 'SERVER_ERROR'}), 500
        else:
            flash('Transfer failed', 'danger')
            return redirect(url_for('accounts.transfer_funds', account_id=account_id))
