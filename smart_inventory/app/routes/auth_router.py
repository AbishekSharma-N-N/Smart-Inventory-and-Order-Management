from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.auth import authenticate_user, create_access_token, verify_token

# Create the router
router = APIRouter(prefix="/auth", tags=["Authentication"])


# ✅ Login endpoint (returns JWT)
@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    token = create_access_token({"sub": user["username"], "role": user["role"]})
    return {"access_token": token, "token_type": "bearer"}


# ✅ Example of a protected endpoint
@router.get("/protected", dependencies=[Depends(verify_token)])
def protected_endpoint():
    return {"message": "You are authorized to access this route 🎉"}
