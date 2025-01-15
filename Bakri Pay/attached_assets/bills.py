from flask import Blueprint, request, jsonify
from sadapay.services.bill_service import BillService
from sadapay.utils.security import jwt_required, get_current_user_id

bills_bp = Blueprint('bills', __name__)


@bills_bp.route('/providers', methods=['GET'])
def get_providers():
    try:
        providers = BillService.get_providers()
        return jsonify([{
            'provider_id': str(prov.provider_id),
            'name': prov.name,
            'category': prov.category
        } for prov in providers]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@bills_bp.route('/pay', methods=['POST'])
@jwt_required
def pay_bill():
    data = request.get_json()
    user_id = get_current_user_id()

    try:
        if not all(k in data for k in ('account_id', 'provider_id', 'consumer_number', 'amount')):
            return jsonify({'error': 'Missing required fields'}), 400

        transaction = BillService.pay_bill(
            user_id=user_id,
            account_id=data['account_id'],
            provider_id=data['provider_id'],
            consumer_number=data['consumer_number'],
            amount=data['amount']
        )

        return jsonify({
            'transaction_id': str(transaction.transaction_id),
            'status': transaction.status
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400
