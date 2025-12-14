# Contributing to CyberPanel

Thank you for your interest in contributing to CyberPanel! This document provides guidelines and information for contributors.

## 🌿 Branch Structure

CyberPanel uses a structured branching strategy to manage development and releases:

### **Branch Types**

1. **`stable`** - Production-ready stable branch
2. **`vX.X.X`** - Version-specific stable branch (e.g., `v2.4.3`)
3. **`vX.X.X-dev`** - Development branch for specific version (e.g., `v2.4.3-dev`)

## 🔄 Development Lifecycle

### **Development Process**

1. **Default Branch**: The latest `vX.X.X-dev` branch serves as the default (master) branch
2. **Contributions**: All contributors must push to the latest `vX.X.X-dev` branch
3. **Stability Check**: Once development is complete and believed to be stable, a new `vX.X.X` stable branch is created from the dev branch
4. **Merge Process**: The `vX.X.X` stable branch is then merged into the main `stable` branch
5. **New Development**: A new `vX.X.X-dev` branch is created and becomes the default branch
6. **Cleanup**: Old dev branches are deleted to save space

### **Important Rules**

- ✅ **DO**: Create pull requests only for the latest dev branch
- ❌ **DON'T**: Create pull requests for any other branches (stable, old dev branches, etc.)
- 🔄 **Development**: All development happens only in the latest dev branch
- 🗑️ **Cleanup**: Old dev branches are deleted after merging to stable

## 🚀 Getting Started

### **Prerequisites**

- Python 3.6+ (see supported versions in README.md)
- Django framework knowledge
- Basic understanding of web hosting control panels
- Git version control

### **Setup Development Environment**

1. **Fork the Repository**
   ```bash
   # Fork the repository on GitHub, then clone your fork
   git clone https://github.com/YOUR_USERNAME/cyberpanel.git
   cd cyberpanel
   ```

2. **Add Upstream Remote**
   ```bash
   git remote add upstream https://github.com/die2mrw007/cyberpanel.git
   ```

3. **Create Development Branch**
   ```bash
   # Checkout the latest dev branch
   git checkout vX.X.X-dev
   git pull upstream vX.X.X-dev
   ```

4. **Install Dependencies**
   ```bash
   # Install Python dependencies
   pip install -r requirements.txt
   ```

## 📝 Making Contributions

### **Code Style Guidelines**

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add comments for complex logic
- Write comprehensive docstrings for functions and classes
- Ensure all code is properly tested

### **Commit Message Format**

Use clear, descriptive commit messages:

```
type(scope): brief description

Detailed description of changes made.
- List specific changes
- Explain why changes were made
- Reference any related issues

Fixes #123
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### **Pull Request Process**

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Write your code
   - Add tests if applicable
   - Update documentation if needed

3. **Test Your Changes**
   ```bash
   # Run tests
   python manage.py test
   
   # Check for linting issues
   flake8 .
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat(module): add new feature"
   ```

5. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a pull request on GitHub targeting the latest dev branch.

## 🧪 Testing

### **Test Requirements**

- All new features must include tests
- Bug fixes must include regression tests
- Ensure all existing tests pass
- Maintain or improve test coverage

### **Running Tests**

```bash
# Run all tests
python manage.py test

# Run specific test module
python manage.py test module_name.tests

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

## 📋 Issue Reporting

### **Before Reporting**

- Check existing issues to avoid duplicates
- Ensure you're using the latest version
- Verify the issue exists in the latest dev branch

### **Issue Template**

When creating an issue, include:

- **OS and Version**: Your operating system and CyberPanel version
- **Steps to Reproduce**: Clear, numbered steps
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Screenshots**: If applicable
- **Logs**: Relevant error logs from `/usr/local/lscp/logs/`

## 🔒 Security

### **Security Issues**

For security-related issues:

- **DO NOT** create public issues
- Email security concerns to: security@cyberpanel.net
- Include detailed information about the vulnerability
- Allow time for the team to address before public disclosure

## 📚 Documentation

### **Documentation Guidelines**

- Update relevant documentation when adding features
- Use clear, concise language
- Include code examples where helpful
- Follow the existing documentation style
- Update README.md if adding new features or changing installation process

## 🤝 Code Review Process

### **Review Criteria**

- Code quality and style
- Test coverage
- Documentation updates
- Security considerations
- Performance impact
- Backward compatibility

### **Review Timeline**

- Initial review: Within 48 hours
- Follow-up reviews: Within 24 hours
- Merge decision: Within 1 week (for approved PRs)

## 🏷️ Release Process

### **Version Numbering**

CyberPanel follows semantic versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### **Release Schedule**

- **Stable Releases**: Monthly or as needed
- **Hotfixes**: As critical issues arise
- **Development**: Continuous integration

## 💬 Community

### **Getting Help**

- 📚 [Documentation](https://raw.githubusercontent.com/die2mrw007/cyberpanel/stable/KnowledgeBase/)
- 💬 [Discord](https://discord.gg/g8k8Db3)
- 📢 [Forums](https://community.cyberpanel.net)
- 📵 [Facebook Group](https://www.facebook.com/groups/cyberpanel)

### **Contributing Guidelines**

- Be respectful and constructive
- Help others learn and grow
- Follow the code of conduct
- Ask questions when unsure

## 📄 License

By contributing to CyberPanel, you agree that your contributions will be licensed under the same license as the project (GPL-3.0).

---

**Thank you for contributing to CyberPanel!** 🎉

Your contributions help make web hosting management easier for thousands of users worldwide.
