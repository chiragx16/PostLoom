from services.auth_utils import role_required

@posts_bp.route("/publish/<slug>", methods=["PUT"])
@role_required(["editor", "admin"])
def publish_post(slug):
    ...