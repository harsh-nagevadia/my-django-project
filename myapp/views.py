from django.shortcuts import render,redirect
from .models import Contact,User,Product,Wishlist,Cart,Transaction
import random
from django.conf import settings
from django.core.mail import send_mail
from .paytm import generate_checksum, verify_checksum
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from django.http import JsonResponse
import os
from twilio.rest import Client

def validate_email(request):
	email=request.GET.get('email')
	data={
		'is_taken':User.objects.filter(email__iexact=email).exists()
	}
	return JsonResponse(data)

def initiate_payment(request):
    user=User.objects.get(email=request.session['email'])
    try:
    	amount = int(request.POST['amount'])
    except:
        return render(request, 'pay.html', context={'error': 'Wrong Accound Details or amount'})

    transaction = Transaction.objects.create(made_by=user,amount=amount)
    transaction.save()
    merchant_key = settings.PAYTM_SECRET_KEY

    params = (
        ('MID', settings.PAYTM_MERCHANT_ID),
        ('ORDER_ID', str(transaction.order_id)),
        ('CUST_ID', str("jigar93776@gmail.com")),
        ('TXN_AMOUNT', str(transaction.amount)),
        ('CHANNEL_ID', settings.PAYTM_CHANNEL_ID),
        ('WEBSITE', settings.PAYTM_WEBSITE),
        # ('EMAIL', request.user.email),
        # ('MOBILE_N0', '9911223388'),
        ('INDUSTRY_TYPE_ID', settings.PAYTM_INDUSTRY_TYPE_ID),
        ('CALLBACK_URL', 'http://localhost:8000/callback/'),
        # ('PAYMENT_MODE_ONLY', 'NO'),
    )

    paytm_params = dict(params)
    checksum = generate_checksum(paytm_params, merchant_key)

    transaction.checksum = checksum
    transaction.save()
    carts=Cart.objects.filter(user=user)
    for i in carts:
    	i.payment_status=True
    	now = datetime.now()
    	dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    	i.payment_date=dt_string
    	i.save()
    paytm_params['CHECKSUMHASH'] = checksum
    print('SENT: ', checksum)
    return render(request, 'redirect.html', context=paytm_params)


@csrf_exempt
def callback(request):
    if request.method == 'POST':
        received_data = dict(request.POST)
        paytm_params = {}
        paytm_checksum = received_data['CHECKSUMHASH'][0]
        for key, value in received_data.items():
            if key == 'CHECKSUMHASH':
                paytm_checksum = value[0]
            else:
                paytm_params[key] = str(value[0])
        # Verify checksum
        is_valid_checksum = verify_checksum(paytm_params, settings.PAYTM_SECRET_KEY, str(paytm_checksum))
        if is_valid_checksum:
            received_data['message'] = "Checksum Matched"
        else:
            received_data['message'] = "Checksum Mismatched"
            return render(request, 'callback.html', context=received_data)
        return render(request, 'callback.html', context=received_data)



def index(request):
	return render(request,'index.html')

def contact(request):
	if request.method=="POST":
		Contact.objects.create(
				name=request.POST['name'],
				email=request.POST['email'],
				phone=request.POST['phone'],
				subject=request.POST['subject'],
				message=request.POST['message']
			)
		msg="Contact Saved Successfully"
		return render(request,'contact.html',{'msg':msg})
	else:
		return render(request,'contact.html')

def signup(request):
	if request.method=="POST":
		try:
			User.objects.get(email=request.POST['email'])
			msg="Email Already Registered"
			return render(request,'signup.html',{'msg':msg})
		except:
			if request.POST['password']==request.POST['cpassword']:
				User.objects.create(
						fname=request.POST['fname'],
						lname=request.POST['lname'],
						email=request.POST['email'],
						mobile=request.POST['mobile'],
						address=request.POST['address'],
						password=request.POST['password'],
						usertype=request.POST['usertype']
					)
				otp=random.randint(1000,9999)
				account_sid = 'ACaa55564e303dd3ecbfc1d8f2fa6f0bc2'
				auth_token = 'ef2401e4282b8533c53871c934a3d9cd'
				client = Client(account_sid, auth_token)
				message = client.messages.create(
         			body='OTP : '+str(otp),
         			from_='+19893092831',
         			to='+919998819757'
     			)

				print(message.sid)
				msg="User Sign Up Successfully"
				return render(request,'login.html',{'msg':msg})
			else:
				msg="Password & Confirm Password Does Not Matched"
				return render(request,'signup.html',{'msg':msg})
	else:
		return render(request,'signup.html')

def login(request):
	if request.method=="POST":
		try:
			user=User.objects.get(
				email=request.POST['email'],
				password=request.POST['password']
			)
			if user.usertype=="user":
				request.session['email']=user.email
				request.session['fname']=user.fname
				wishlists=Wishlist.objects.filter(user=user)
				request.session['wishlist_count']=len(wishlists)
				carts=Cart.objects.filter(user=user)
				request.session['cart_count']=len(carts)
				return render(request,'index.html')
			elif user.usertype=="seller":
				products=Product.objects.filter(seller=user)
				request.session['email']=user.email
				request.session['fname']=user.fname
				request.session['product_count']=len(products)
				return render(request,'seller_index.html')
		except:
			msg="EMail or Password Is Incorrect"
			return render(request,'login.html',{'msg':msg})
	else:
		return render(request,'login.html')

def logout(request):
	try:
		del request.session['email']
		del request.session['fname']
		msg="User Logout Successfully"
		return render(request,'login.html',{'msg':msg})
	except:
		return render(request,'login.html')

def change_password(request):
	if request.method=="POST":
		user=User.objects.get(email=request.session['email'])
		if user.password==request.POST['old_password']:
			if request.POST['new_password']==request.POST['cnew_password']:
				user.password=request.POST['new_password']
				user.save()
				return redirect('logout')
			else:
				msg="New Password & Confirm New Password Does Not Matched"
				return render(request,'change_password.html',{'msg':msg})
		else:
			msg="Old Password Does Not Matched"
			return render(request,'change_password.html',{'msg':msg})	
	else:
		return render(request,'change_password.html')

def seller_change_password(request):
	if request.method=="POST":
		user=User.objects.get(email=request.session['email'])
		if user.password==request.POST['old_password']:
			if request.POST['new_password']==request.POST['cnew_password']:
				user.password=request.POST['new_password']
				user.save()
				return redirect('logout')
			else:
				msg="New Password & Confirm New Password Does Not Matched"
				return render(request,'seller_change_password.html',{'msg':msg})
		else:
			msg="Old Password Does Not Matched"
			return render(request,'seller_change_password.html',{'msg':msg})	
	else:
		return render(request,'seller_change_password.html')

def seller_add_product(request):
	if request.method=="POST":
		seller=User.objects.get(email=request.session['email'])
		Product.objects.create(
				seller=seller,
				product_name=request.POST['product_name'],
				product_price=request.POST['product_price'],
				product_image=request.FILES['product_image'],
				product_desc=request.POST['product_desc']
			)
		msg="Product Added Successfully"
		products=Product.objects.filter(seller=seller)
		request.session['product_count']=len(products)
		return render(request,'seller_add_product.html',{'msg':msg})
	else:
		return render(request,'seller_add_product.html')

def seller_index(request):
	return render(request,'seller_index.html')

def seller_view_product(request):
	seller=User.objects.get(email=request.session['email'])
	products=Product.objects.filter(seller=seller)
	return render(request,'seller_view_product.html',{'products':products})

def seller_product_details(request,pk):
	product=Product.objects.get(pk=pk)
	return render(request,'seller_product_details.html',{'product':product})

def seller_edit_product(request,pk):
	product=Product.objects.get(pk=pk)
	if request.method=="POST":
		product.product_name=request.POST['product_name']
		product.product_price=request.POST['product_price']
		product.product_desc=request.POST['product_desc']
		try:
			product.product_image=request.FILES['product_image']
		except:
			pass
		product.save()
		msg="Product Edited Successfully"
		return render(request,'seller_edit_product.html',{'product':product,'msg':msg})
	else:
		return render(request,'seller_edit_product.html',{'product':product})

def seller_delete_product(request,pk):
	seller=User.objects.get(email=request.session['email'])
	product=Product.objects.get(pk=pk)
	product.delete()
	products=Product.objects.filter(seller=seller)
	request.session['product_count']=len(products)
	return redirect('seller_view_product')

def shop(request):
	products=Product.objects.all()
	return render(request,'shop.html',{'products':products})

def checkout(request):
	return render(request,'checkout.html')

def cart(request):
	subtotal=0
	coupon=0
	user=User.objects.get(email=request.session['email'])
	carts=Cart.objects.filter(user=user,payment_status=False)
	shipping=5*len(carts)
	request.session['cart_count']=len(carts)
	for i in carts:
		subtotal=subtotal+i.total_price
	netprice=subtotal+shipping

	if request.method!="POST":
		if netprice>500:
			coupon="FIRST10"
			subject = "Coupon Code"
			message = "Hello, "+user.fname+".\n You Are Eligible For Discount."+" Your Coupon Code Is "+str(coupon)+". \nApply This At Checkout Page."
			email_from = settings.EMAIL_HOST_USER
			recipient_list = [user.email,]
			#send_mail( subject, message, email_from, recipient_list )
			return render(request,'cart.html',{'carts':carts,'subtotal':subtotal,'shipping':shipping,'netprice':netprice,'coupon':coupon})
		else:
			return render(request,'cart.html',{'carts':carts,'subtotal':subtotal,'shipping':shipping,'netprice':netprice,'coupon':coupon})
	else:
		if request.POST['coupon_code']==request.POST['coupon']:
			discount=(netprice*10)/100
			netprice=netprice-discount
			msg="Coupon Code Applied Successfully"
			return render(request,'cart.html',{'carts':carts,'subtotal':subtotal,'shipping':shipping,'netprice':netprice,'msg':msg,'coupon':coupon})
		else:
			msg="Coupon Code Invalid"
			coupon="FIRST10"
			subject = "Coupon Code"
			message = "Hello, "+user.fname+".\n You Are Eligible For Discount."+" Your Coupon Code Is "+str(coupon)+". \nApply This At Checkout Page."
			email_from = settings.EMAIL_HOST_USER
			recipient_list = [user.email,]
			send_mail( subject, message, email_from, recipient_list )
			return render(request,'cart.html',{'carts':carts,'subtotal':subtotal,'shipping':shipping,'netprice':netprice,'coupon':coupon,'msg':msg})
		
def wishlist(request):
	user=User.objects.get(email=request.session['email'])
	wishlists=Wishlist.objects.filter(user=user)
	request.session['wishlist_count']=len(wishlists)
	return render(request,'wishlist.html',{'wishlists':wishlists})

def add_to_wishlist(request,pk):
	product=Product.objects.get(pk=pk)
	user=User.objects.get(email=request.session['email'])
	Wishlist.objects.create(
			user=user,
			product=product
		)
	return redirect('wishlist')

def product_details(request,pk):
	wishlist_flag=False
	cart_flag=False
	user=User()
	product=Product.objects.get(pk=pk)
	try:
		user=User.objects.get(email=request.session['email'])
	except:
		pass
	try:
		Wishlist.objects.get(user=user,product=product)
		wishlist_flag=True
	except:
		pass
	try:
		Cart.objects.get(user=user,product=product,payment_status=False)
		cart_flag=True
	except:
		pass
	return render(request,'product_details.html',{'product':product,'wishlist_flag':wishlist_flag,'cart_flag':cart_flag})

def remove_from_wishlist(request,pk):
	product=Product.objects.get(pk=pk)
	user=User.objects.get(email=request.session['email'])
	wishlist=Wishlist.objects.get(user=user,product=product)
	wishlist.delete()
	return redirect('wishlist')

def add_to_cart(request,pk):
	product=Product.objects.get(pk=pk)
	user=User.objects.get(email=request.session['email'])
	Cart.objects.create(
			user=user,
			product=product,
			product_price=product.product_price,
			total_price=product.product_price
		)
	return redirect('cart')

def remove_from_cart(request,pk):
	product=Product.objects.get(pk=pk)
	user=User.objects.get(email=request.session['email'])
	cart=Cart.objects.get(user=user,product=product)
	cart.delete()
	return redirect('cart')

def change_qty(request):
	cart=Cart.objects.get(pk=request.POST['id'])
	product_qty=request.POST['product_qty']
	cart.product_qty=product_qty
	cart.total_price=int(product_qty)*int(cart.product_price)
	cart.save()
	return redirect('cart')

def myorders(request):
	user=User.objects.get(email=request.session['email'])
	carts=Cart.objects.filter(user=user,payment_status=True)
	return render(request,'myorders.html',{'carts':carts})

def search(request):
	search=request.POST['search'].title()
	products=Product.objects.filter(product_name=search)
	print(products)
	return render(request,'search.html',{'products':products})

def forgot_password(request):
	print("forgot password called")
	if request.method=="POST":
		try:
			user=User.objects.get(email=request.POST['email'])
			subject = 'OTP For Forgot Password'
			otp=random.randint(1000,9999)
			message = 'OTP For Forgot Password Is '+str(otp)
			email_from = settings.EMAIL_HOST_USER
			recipient_list = [user.email,]
			send_mail( subject, message, email_from, recipient_list )
			print("otp sent")
			return render(request,'otp.html',{'email':user.email,'otp':otp})
		except:
			msg="Email Does Not Exists"
			return render(request,'forgot_password.html',{'msg':msg})
	else:
		return render(request,'forgot_password.html')

def verify_otp(request):
	email=request.POST['email']
	otp1=request.POST['otp1']
	otp2=request.POST['otp2']

	if otp1==otp2:
		return render(request,'new_password.html',{'email':email})
	else:
		msg="Invalid OTP"
		return render(request,'otp.html',{'email':email,'otp':otp,'msg':msg})

def new_password(request):
	np=request.POST['new_password']
	cnp=request.POST['cnew_password']
	email=request.POST['email']

	if np==cnp:
		user=User.objects.get(email=email)
		user.password=np
		user.save()
		return redirect('login')
	else:
		msg="New Password & Confirm New Password Does Not Matched"
		return render(request,'new_password.html',{'email':email,'msg':msg})