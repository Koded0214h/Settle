from datetime import timedelta
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from mixer.backend.django import mixer

from invoices.models import Invoice
from users.models import User


class InvoiceCreationTest(APITestCase):
    def setUp(self):
        self.user = mixer.blend(User, email='test@example.com', password='password123', is_verified=True, wallet_address='0x' + 'a' * 40)
        self.client.force_authenticate(user=self.user)
        self.create_url = reverse('invoice_list')
        
        self.valid_payload_email = {
            'title': 'Test Invoice via Email',
            'description': 'A test invoice for email client.',
            'client_email': 'client@example.com',
            'amount': '100.000000',
            'currency': 'USDC',
            'due_date': (timezone.now() + timedelta(days=7)).isoformat(),
            'items': [
                {'description': 'Item 1', 'quantity': '1', 'unit_price': '50.000000'},
                {'description': 'Item 2', 'quantity': '2', 'unit_price': '25.000000'}
            ]
        }
        
        self.valid_payload_wallet = {
            'title': 'Test Invoice via Wallet',
            'description': 'A test invoice for wallet client.',
            'client_wallet': '0x' + 'b' * 40,
            'amount': '200.000000',
            'currency': 'USDC',
            'due_date': (timezone.now() + timedelta(days=14)).isoformat(),
            'items': []
        }

    @patch('invoices.tasks.send_invoice_notification.delay')
    @patch('invoices.tasks.create_invoice_on_chain.delay')
    def test_create_invoice_with_email_client_success(self, mock_create_on_chain, mock_send_notification):
        response = self.client.post(self.create_url, self.valid_payload_email, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Invoice.objects.count(), 1)
        invoice = Invoice.objects.first()
        self.assertEqual(invoice.title, 'Test Invoice via Email')
        self.assertEqual(invoice.client_email, 'client@example.com')
        self.assertEqual(invoice.creator, self.user)
        self.assertEqual(invoice.items.count(), 2)
        mock_send_notification.assert_called_once_with(invoice.id)
        mock_create_on_chain.assert_not_called()  # Should not be called for email client

    @patch('invoices.tasks.send_invoice_notification.delay')
    @patch('invoices.tasks.create_invoice_on_chain.delay')
    def test_create_invoice_with_wallet_client_success(self, mock_create_on_chain, mock_send_notification):
        response = self.client.post(self.create_url, self.valid_payload_wallet, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Invoice.objects.count(), 1)
        invoice = Invoice.objects.first()
        self.assertEqual(invoice.title, 'Test Invoice via Wallet')
        self.assertEqual(invoice.client_wallet, '0x' + 'b' * 40)
        mock_send_notification.assert_called_once_with(invoice.id)
        mock_create_on_chain.assert_called_once_with(str(invoice.id))  # Should be called for wallet client

    def test_create_invoice_missing_client_info_failure(self):
        invalid_payload = self.valid_payload_email.copy()
        del invalid_payload['client_email']
        response = self.client.post(self.create_url, invalid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Either client_email or client_wallet must be provided.', str(response.content))
        self.assertEqual(Invoice.objects.count(), 0)
    
    def test_create_invoice_invalid_wallet_format_failure(self):
        invalid_payload = self.valid_payload_wallet.copy()
        invalid_payload['client_wallet'] = '0x123'  # Too short
        response = self.client.post(self.create_url, invalid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Invalid Ethereum address format.', str(response.content))
        self.assertEqual(Invoice.objects.count(), 0)

    def test_create_invoice_due_date_in_past_failure(self):
        invalid_payload = self.valid_payload_email.copy()
        invalid_payload['due_date'] = (timezone.now() - timedelta(days=1)).isoformat()
        response = self.client.post(self.create_url, invalid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Due date must be in the future.', str(response.content))
        self.assertEqual(Invoice.objects.count(), 0)

    def test_unauthenticated_create_invoice_failure(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(self.create_url, self.valid_payload_email, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Invoice.objects.count(), 0)
