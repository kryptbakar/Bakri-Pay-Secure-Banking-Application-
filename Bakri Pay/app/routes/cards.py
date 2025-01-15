import logging

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from werkzeug.exceptions import BadRequest, NotFound, Forbidden
from flask_login import login_required, current_user

from app.services.card_service import CardService

cards_bp = Blueprint('cards', __name__)
logger = logging.getLogger(__name__)


@cards_bp.route('/', methods=['GET'])
@login_required
def get_cards():
    """Get all cards for authenticated user"""
    try:
        account_id = request.args.get('account_id')

        cards = CardService.get_user_cards(current_user.user_id, account_id)

        logger.info(f"Retrieved cards for user {current_user.user_id}")
        
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify([{
                'card_id': card['card_id'],
                'last_four': card['last_four'],
                'expiry_date': card['expiry_date'],
                'is_virtual': card['is_virtual'],
                'is_active': card['is_active'],
                'created_at': card['created_at']
            } for card in cards]), 200
        else:
            return render_template('cards.html', cards=cards, account_id=account_id)

    except Forbidden as e:
        logger.warning(f"Unauthorized card access attempt by user {current_user.user_id}")
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': str(e), 'code': 'UNAUTHORIZED_ACCESS'}), 403
        else:
            flash('You do not have access to this account', 'danger')
            return redirect(url_for('accounts.dashboard'))
    except Exception as e:
        logger.error(f"Failed to get cards: {str(e)}")
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': 'Failed to retrieve cards', 'code': 'SERVER_ERROR'}), 500
        else:
            flash('Failed to retrieve cards', 'danger')
            return redirect(url_for('accounts.dashboard'))


@cards_bp.route('/', methods=['POST'])
@login_required
def create_card():
    """Create a new card (virtual or physical)"""
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form

        if not data or not all(k in data for k in ('account_id', 'is_virtual')):
            raise BadRequest(description='Missing required fields: account_id and is_virtual')
            
        # Convert is_virtual to boolean if needed
        is_virtual = data['is_virtual']
        if isinstance(is_virtual, str):
            is_virtual = is_virtual.lower() in ('true', 'yes', '1')

        if is_virtual:
            card = CardService.create_virtual_card(current_user.user_id, data['account_id'])
        else:
            if 'delivery_address' not in data:
                raise BadRequest(description='Physical cards require delivery_address')
                
            # Parse address data
            if isinstance(data['delivery_address'], str):
                import json
                try:
                    address = json.loads(data['delivery_address'])
                except:
                    address = {
                        'line1': data.get('address_line1', ''),
                        'line2': data.get('address_line2', ''),
                        'city': data.get('city', ''),
                        'state': data.get('state', ''),
                        'postal_code': data.get('postal_code', ''),
                        'country': data.get('country', '')
                    }
            else:
                address = data['delivery_address']
                
            card = CardService.request_physical_card(
                current_user.user_id,
                data['account_id'],
                address
            )

        logger.info(f"Created new card {card['card_id']} for user {current_user.user_id}")
        
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify(card), 201
        else:
            flash('Card created successfully', 'success')
            return redirect(url_for('cards.get_cards', account_id=data['account_id']))

    except BadRequest as e:
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': str(e), 'code': 'VALIDATION_ERROR'}), 400
        else:
            flash(str(e), 'danger')
            return redirect(url_for('accounts.dashboard'))
    except Forbidden as e:
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': str(e), 'code': 'UNAUTHORIZED_ACCESS'}), 403
        else:
            flash('You do not have access to this account', 'danger')
            return redirect(url_for('accounts.dashboard'))
    except Exception as e:
        logger.error(f"Card creation failed: {str(e)}")
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': 'Card creation failed', 'code': 'SERVER_ERROR'}), 500
        else:
            flash('Card creation failed', 'danger')
            return redirect(url_for('accounts.dashboard'))


@cards_bp.route('/<card_id>/status', methods=['PUT', 'POST'])
@login_required
def update_card_status(card_id):
    """Activate or deactivate a card"""
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form

        if not data or 'activate' not in data:
            raise BadRequest(description='Missing activate parameter')
            
        # Convert to boolean if needed
        activate = data['activate']
        if isinstance(activate, str):
            activate = activate.lower() in ('true', 'yes', '1', 'on')

        card = CardService.toggle_card_status(
            user_id=current_user.user_id,
            card_id=card_id,
            activate=activate
        )

        logger.info(f"Updated status for card {card_id} to {'active' if activate else 'inactive'}")
        
        if request.is_json or request.method == 'PUT' or request.headers.get('Accept') == 'application/json':
            return jsonify(card), 200
        else:
            flash(f"Card {'activated' if activate else 'deactivated'} successfully", 'success')
            return redirect(url_for('cards.get_cards'))

    except NotFound as e:
        if request.is_json or request.method == 'PUT' or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': str(e), 'code': 'CARD_NOT_FOUND'}), 404
        else:
            flash('Card not found', 'danger')
            return redirect(url_for('cards.get_cards'))
    except Forbidden as e:
        if request.is_json or request.method == 'PUT' or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': str(e), 'code': 'UNAUTHORIZED_ACCESS'}), 403
        else:
            flash('You do not have access to this card', 'danger')
            return redirect(url_for('cards.get_cards'))
    except Exception as e:
        logger.error(f"Failed to update card status: {str(e)}")
        if request.is_json or request.method == 'PUT' or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': 'Status update failed', 'code': 'SERVER_ERROR'}), 500
        else:
            flash('Status update failed', 'danger')
            return redirect(url_for('cards.get_cards'))


@cards_bp.route('/<card_id>/report', methods=['POST'])
@login_required
def report_card(card_id):
    """Report card as lost/stolen and request replacement"""
    try:
        replacement = CardService.report_card_lost_or_stolen(current_user.user_id, card_id)

        logger.warning(f"User {current_user.user_id} reported card {card_id} as lost/stolen")
        
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify(replacement), 200
        else:
            flash('Card reported as lost/stolen and replacement issued', 'success')
            return redirect(url_for('cards.get_cards'))

    except NotFound as e:
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': str(e), 'code': 'CARD_NOT_FOUND'}), 404
        else:
            flash('Card not found', 'danger')
            return redirect(url_for('cards.get_cards'))
    except Forbidden as e:
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': str(e), 'code': 'UNAUTHORIZED_ACCESS'}), 403
        else:
            flash('You do not have access to this card', 'danger')
            return redirect(url_for('cards.get_cards'))
    except Exception as e:
        logger.error(f"Failed to report card: {str(e)}")
        if request.is_json or request.headers.get('Accept') == 'application/json':
            return jsonify({'error': 'Card report failed', 'code': 'SERVER_ERROR'}), 500
        else:
            flash('Card report failed', 'danger')
            return redirect(url_for('cards.get_cards'))
