import logging

from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest, NotFound, Forbidden

from ..services.card_service import CardService
from ..utils.security import login_required, get_current_user_id

cards_bp = Blueprint('cards', __name__)
logger = logging.getLogger(__name__)


@cards_bp.route('/', methods=['GET'])
@login_required
def get_cards():
    """
    Get all cards for authenticated user
    ---
    tags:
      - Cards
    parameters:
      - name: account_id
        in: query
        type: string
        description: Filter cards by account
    responses:
      200:
        description: List of user's cards
        schema:
          type: array
          items:
            $ref: '#/definitions/Card'
      401:
        $ref: '#/responses/Unauthorized'
    """
    try:
        user_id = get_current_user_id()
        account_id = request.args.get('account_id')

        cards = CardService.get_user_cards(user_id, account_id)

        logger.info(f"Retrieved cards for user {user_id}")
        return jsonify([{
            'card_id': str(card['card_id']),
            'last_four': card['last_four'],
            'expiry_date': card['expiry_date'],
            'is_virtual': card['is_virtual'],
            'is_active': card['is_active'],
            'created_at': card['created_at']
        } for card in cards]), 200

    except Forbidden as e:
        logger.warning(f"Unauthorized card access attempt by user {user_id}")
        return jsonify({'error': str(e), 'code': 'UNAUTHORIZED_ACCESS'}), 403
    except Exception as e:
        logger.error(f"Failed to get cards: {str(e)}")
        return jsonify({'error': 'Failed to retrieve cards', 'code': 'SERVER_ERROR'}), 500


@cards_bp.route('/', methods=['POST'])
@login_required
def create_card():
    """
    Create a new card (virtual or physical)
    ---
    tags:
      - Cards
    parameters:
      - name: body
        in: body
        required: true
        schema:
          $ref: '#/definitions/CreateCardRequest'
    responses:
      201:
        description: Card created successfully
        schema:
          $ref: '#/definitions/Card'
      400:
        $ref: '#/responses/BadRequest'
      403:
        $ref: '#/responses/Forbidden'
    """
    try:
        user_id = get_current_user_id()
        data = request.get_json()

        if not data or not all(k in data for k in ('account_id', 'is_virtual')):
            raise BadRequest(description='Missing required fields: account_id and is_virtual')

        if data.get('is_virtual'):
            card = CardService.create_virtual_card(user_id, data['account_id'])
        else:
            if 'delivery_address' not in data:
                raise BadRequest(description='Physical cards require delivery_address')
            card = CardService.request_physical_card(
                user_id,
                data['account_id'],
                data['delivery_address']
            )

        logger.info(f"Created new card {card['card_id']} for user {user_id}")
        return jsonify(card), 201

    except BadRequest as e:
        return jsonify({'error': str(e), 'code': 'VALIDATION_ERROR'}), 400
    except Forbidden as e:
        return jsonify({'error': str(e), 'code': 'UNAUTHORIZED_ACCESS'}), 403
    except Exception as e:
        logger.error(f"Card creation failed: {str(e)}")
        return jsonify({'error': 'Card creation failed', 'code': 'SERVER_ERROR'}), 500


@cards_bp.route('/<card_id>/status', methods=['PUT'])
@login_required
def update_card_status(card_id):
    """
    Activate or deactivate a card
    ---
    tags:
      - Cards
    parameters:
      - name: card_id
        in: path
        required: true
        type: string
      - name: body
        in: body
        required: true
        schema:
          $ref: '#/definitions/UpdateCardStatusRequest'
    responses:
      200:
        description: Card status updated
        schema:
          $ref: '#/definitions/Card'
      403:
        $ref: '#/responses/Forbidden'
      404:
        $ref: '#/responses/NotFound'
    """
    try:
        user_id = get_current_user_id()
        data = request.get_json()

        if not data or 'activate' not in data:
            raise BadRequest(description='Missing activate parameter')

        card = CardService.toggle_card_status(
            user_id=user_id,
            card_id=card_id,
            activate=data['activate']
        )

        logger.info(f"Updated status for card {card_id} to {'active' if data['activate'] else 'inactive'}")
        return jsonify(card), 200

    except NotFound as e:
        return jsonify({'error': str(e), 'code': 'CARD_NOT_FOUND'}), 404
    except Forbidden as e:
        return jsonify({'error': str(e), 'code': 'UNAUTHORIZED_ACCESS'}), 403
    except Exception as e:
        logger.error(f"Failed to update card status: {str(e)}")
        return jsonify({'error': 'Status update failed', 'code': 'SERVER_ERROR'}), 500


@cards_bp.route('/<card_id>/report', methods=['POST'])
@login_required
def report_card(card_id):
    """
    Report card as lost/stolen and request replacement
    ---
    tags:
      - Cards
    parameters:
      - name: card_id
        in: path
        required: true
        type: string
    responses:
      200:
        description: Card reported and replacement issued
        schema:
          $ref: '#/definitions/CardReplacement'
      403:
        $ref: '#/responses/Forbidden'
      404:
        $ref: '#/responses/NotFound'
    """
    try:
        user_id = get_current_user_id()

        replacement = CardService.report_card_lost_or_stolen(user_id, card_id)

        logger.warning(f"User {user_id} reported card {card_id} as lost/stolen")
        return jsonify(replacement), 200

    except NotFound as e:
        return jsonify({'error': str(e), 'code': 'CARD_NOT_FOUND'}), 404
    except Forbidden as e:
        return jsonify({'error': str(e), 'code': 'UNAUTHORIZED_ACCESS'}), 403
    except Exception as e:
        logger.error(f"Failed to report card: {str(e)}")
        return jsonify({'error': 'Card report failed', 'code': 'SERVER_ERROR'}), 500
